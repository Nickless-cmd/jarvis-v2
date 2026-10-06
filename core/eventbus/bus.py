from __future__ import annotations

import collections
import json
import logging
import queue
import sqlite3
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.eventbus.events import Event
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_WRITER_QUEUE_MAXSIZE = 10_000
# Hvor mange egne event-id'er der huskes. Relæet poller hvert sekund, så
# vinduet skal kun dække det relæet ikke har nået endnu — rigeligt.
_EGNE_IDS_MAX = 50_000
# Batch up to this many already-queued events into ONE SQLite transaction. Under a
# burst (heartbeat storm / busy agentic loop) this collapses hundreds of per-event
# commits into a handful → far fewer WAL write-lock acquisitions → API chat/cost
# writes stop busy-waiting up to busy_timeout (5s) behind the event-writer. At low
# volume the drain finds the queue empty and writes a single event (no added latency).
_WRITER_BATCH_MAX = 128
_FLUSH_POLL_SECS = 0.001
_WRITER_SHUTDOWN_TIMEOUT = 5.0

# Dead-letter: en batch der ikke kunne committes SKRIVES til disk i stedet for at
# blive kastet. Målt 6/10-2026: uden dette var tabet endeligt — rækken nåede
# hverken events-tabellen eller abonnenterne, og hverken krydsproces-relæet
# (krydsproces.py) eller de fem poll-veje (recent_since_id) kunne genskabe den,
# fordi de alle læser tabellen hvor rækken aldrig kom. Filen er append-only og
# rører ikke DB'en, så den kan skrives netop når DB'en er låst.
_DEAD_LETTER_FILENAME = "eventbus_dead_letter.jsonl"
# Hvor tit writer'en forsøger at genindlæse filen — kun når køen er tom (roligt).
_DRAIN_INTERVAL_SECS = 60.0


class EventBus:
    """Thread-safe event bus with async SQLite writes.

    publish() queues the event to a dedicated writer thread for SQLite
    INSERT + causal edges, then notifies subscribers AFTER the write
    commits.  This decouples fast publish-callers (service threads,
    agentic loops) from slow SQLite I/O.

    Thread safety — the writer is a single thread processing a FIFO
    queue, so events are committed in publish order.  Subscriber
    notification runs on the writer thread but is *non-blocking*
    (queue.put_nowait on each subscriber's in-memory queue), so the
    writer is never stalled by slow subscribers.

    flush() is provided for tests that need to read their writes back
    synchronously.
    """

    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[dict[str, Any] | None]] = []
        self._lock = threading.Lock()

        # ---- Async writer machinery ----
        self._writer_queue: queue.Queue[dict[str, Any] | None] = queue.Queue(
            maxsize=_WRITER_QUEUE_MAXSIZE
        )
        self._seq_lock = threading.Lock()
        self._publish_seq: int = 0  # incremented per publish (next seq to hand out)
        self._write_seq: int = 0  # seq of the last committed event

        # Id'er på events DENNE proces har skrevet. Krydsproces-relæet
        # (core/eventbus/krydsproces.py) springer dem over, så en lokal
        # abonnent aldrig får samme event to gange. Noteres FØR commit —
        # en anden forbindelse kan ikke se rækken før den er committed.
        self._egne_ids: collections.deque[int] = collections.deque(maxlen=_EGNE_IDS_MAX)
        self._egne_set: set[int] = set()
        self._egne_lock = threading.Lock()

        # Dead-letter-tilstand (se _DEAD_LETTER_FILENAME). Tællerne lever kun i
        # denne proces; FILEN er den durable sandhed på tværs af genstarter.
        self._dead_letter_lock = threading.Lock()
        self._spilled_total = 0
        self._drained_total = 0
        self._last_drain_attempt = 0.0

        self._writer_shutdown = threading.Event()
        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name="eventbus-writer",
        )
        self._writer_thread.start()

    # ---- Public API ---------------------------------------------------

    def publish(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        caused_by: int | list[int] | None = None,
        edge_kind: str = "triggered",
    ) -> None:
        """Publish an event.  Returns immediately — the actual write is async."""
        # Resolve parent (EventContext if caller didn't provide explicit).
        if caused_by is None:
            try:
                from core.eventbus.context import get_current_event

                caused_by = get_current_event()
            except Exception:
                caused_by = None

        event = Event.create(kind=kind, payload=payload)
        payload_json = json.dumps(event.payload, ensure_ascii=False)
        created_at = event.ts.isoformat()

        # Serialise all data the writer needs so we don't hold references.
        item: dict[str, Any] = {
            "kind": event.kind,
            "payload": event.payload,
            "payload_json": payload_json,
            "created_at": created_at,
            "caused_by": caused_by,
            "edge_kind": edge_kind,
        }

        with self._seq_lock:
            seq = self._publish_seq
            self._publish_seq += 1
        # seq tracks "the Nth event published" (1-based), not the 0-based index.
        # This way flush() can compare write_seq >= publish_seq directly.
        seq = seq + 1
        item["seq"] = seq

        try:
            self._writer_queue.put_nowait(item)
        except queue.Full:
            logger.error(
                "eventbus-writer queue FULL (limit=%d) — dropping event kind=%s seq=%d",
                _WRITER_QUEUE_MAXSIZE,
                kind,
                seq,
            )
            # Still advance write_seq so flush() doesn't wait forever for
            # an event we'll never process.
            with self._seq_lock:
                self._write_seq = seq

    def flush(self, timeout: float = 10.0) -> None:
        """Block until the writer has committed *all* events published so far.

        Intended for tests.  Production code should not need this.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._seq_lock:
                if self._write_seq >= self._publish_seq:
                    return
            time.sleep(_FLUSH_POLL_SECS)
        logger.warning(
            "eventbus.flush() timed out after %.1fs — "
            "publish_seq=%d write_seq=%d queue_size=%d",
            timeout,
            self._publish_seq,
            self._write_seq,
            self._writer_queue.qsize(),
        )

    def stop(self) -> None:
        """Graceful shutdown: drain the writer thread."""
        self._writer_shutdown.set()
        self._writer_queue.put(None)  # poison pill wakes writer
        self._writer_thread.join(timeout=_WRITER_SHUTDOWN_TIMEOUT)
        if self._writer_thread.is_alive():
            logger.warning("eventbus-writer did not exit within timeout")

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, payload_json, created_at
                FROM events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            self._deserialize_row(
                event_id=int(row["id"]),
                kind=row["kind"],
                payload_json=row["payload_json"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def recent_by_family(self, family: str, *, limit: int = 50) -> list[dict[str, Any]]:
        family_clean = str(family or "").strip()
        if not family_clean:
            return []
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, payload_json, created_at
                FROM events
                WHERE kind LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (f"{family_clean}.%", max(int(limit), 1)),
            ).fetchall()
        return [
            self._deserialize_row(
                event_id=int(row["id"]),
                kind=row["kind"],
                payload_json=row["payload_json"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def recent_since_id(self, after_id: int, *, limit: int = 100) -> list[dict[str, Any]]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, payload_json, created_at
                FROM events
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (max(int(after_id), 0), max(int(limit), 1)),
            ).fetchall()
        return [
            self._deserialize_row(
                event_id=int(row["id"]),
                kind=row["kind"],
                payload_json=row["payload_json"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def subscribe(self) -> queue.Queue[dict[str, Any] | None]:
        subscriber: queue.Queue[dict[str, Any] | None] = queue.Queue()
        with self._lock:
            self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[dict[str, Any] | None]) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)
        subscriber.put_nowait(None)

    # ---- Writer thread -------------------------------------------------

    def _writer_loop(self) -> None:
        """Dedicated thread: pull items from queue, write to SQLite, notify."""
        while not self._writer_shutdown.is_set():
            try:
                item = self._writer_queue.get(timeout=0.5)
            except queue.Empty:
                self._maaske_drain()
                continue

            if item is None:  # poison pill
                break

            # Drain any co-queued events into ONE batch/transaction. FIFO preserved.
            batch: list[dict[str, Any]] = [item]
            poison = False
            while len(batch) < _WRITER_BATCH_MAX:
                try:
                    nxt = self._writer_queue.get_nowait()
                except queue.Empty:
                    break
                if nxt is None:
                    poison = True
                    break
                batch.append(nxt)

            try:
                self._write_events_batch(batch)
            except sqlite3.OperationalError:
                # Rygraden: DB-lås trods busy_timeout (fx lang checkpoint) → ét retry efter
                # kort pause. Går det også galt, SPILLES batchen til disk — den kastes
                # aldrig (se _spill_batch). Før 6/10-2026 blev den kastet her.
                time.sleep(0.2)
                try:
                    self._write_events_batch(batch)
                except Exception as retry_exc:
                    self._spill_batch(batch, retry_exc)
            except Exception as exc:
                self._spill_batch(batch, exc)
            finally:
                # Always advance the sequence so flush() doesn't deadlock.
                max_seq = max((it.get("seq", -1) for it in batch), default=-1)
                with self._seq_lock:
                    if max_seq >= self._write_seq:
                        self._write_seq = max_seq

            if poison:
                break

    # ---- Dead-letter: tab bliver forsinkelse, ikke hul -----------------

    def _dead_letter_path(self) -> Path:
        """Stien til spill-filen. Læses lazy, så DB_PATH kan omdirigeres i tests."""
        from core.runtime.db_core import DB_PATH

        return Path(DB_PATH).parent / _DEAD_LETTER_FILENAME

    def _spill_batch(
        self, batch: list[dict[str, Any]], exc: BaseException | None
    ) -> None:
        """Skriv en batch der ikke kunne committes til dead-letter-filen.

        Filen er append-only og rører ikke DB'en — derfor kan den skrives netop
        når DB'en er låst, hvilket er den eneste situation hvor vi er her.
        Fejler spillet selv, falder vi tilbage til det gamle tab (logget).
        """
        linjer: list[str] = []
        for item in batch:
            post = dict(item)
            post["spilled_at"] = datetime.now(UTC).isoformat()
            try:
                linjer.append(json.dumps(post, ensure_ascii=False))
            except (TypeError, ValueError):
                # En payload der ikke kan serialiseres kan ikke genindlæses —
                # den ene linje tabes, resten af batchen reddes.
                logger.warning(
                    "eventbus-writer: kunne ikke serialisere %r til dead-letter",
                    post.get("kind"),
                )
        if not linjer:
            return
        try:
            path = self._dead_letter_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            with self._dead_letter_lock:
                with path.open("a", encoding="utf-8") as fh:
                    fh.write("\n".join(linjer) + "\n")
            self._spilled_total += len(linjer)
            logger.warning(
                "eventbus-writer: %d events spillet til disk efter fejlet skrivning (%s)",
                len(linjer),
                exc,
            )
        except Exception:
            logger.exception(
                "eventbus-writer: dropped %d events — spill til disk fejlede", len(batch)
            )

    def _drain_dead_letter(self) -> int:
        """Genindlæs spillede events. Returnerer antal skrevet tilbage til DB'en.

        Rækkerne får NYE id'er, så krydsproces-relæet og poll-vejene ser dem (de
        læser recent_since_id), og lokale abonnenter får notifikationen gennem
        den normale commit-vej. `created_at` bevares, så eventet beholder sin
        ægte tid. Kun linjer der faktisk blev skrevet fjernes fra filen.
        """
        path = self._dead_letter_path()
        with self._dead_letter_lock:
            if not path.exists():
                return 0
            try:
                raa = path.read_text(encoding="utf-8")
            except OSError:  # filen kan ikke læses — behandl den som tom
                return 0
            poster: list[dict[str, Any]] = []
            for linje in raa.splitlines():
                if not linje.strip():
                    continue
                try:
                    poster.append(json.loads(linje))
                except (TypeError, ValueError):
                    continue  # korrupt linje kan ikke genindlæses — spring den over
            if not poster:
                try:
                    path.write_text("", encoding="utf-8")
                except OSError:  # kan ikke tømme filen nu — næste drain forsøger igen
                    pass
                return 0

            skrevet = 0
            rest: list[dict[str, Any]] = []
            for i in range(0, len(poster), _WRITER_BATCH_MAX):
                chunk = poster[i : i + _WRITER_BATCH_MAX]
                try:
                    self._write_events_batch(chunk)
                    skrevet += len(chunk)
                except Exception:
                    # Stadig låst — behold alt fra og med denne chunk til næste
                    # rolige vindue. Intet kastes.
                    rest = poster[i:]
                    break

            try:
                tmp = path.with_name(path.name + ".tmp")
                tmp.write_text(
                    "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in rest),
                    encoding="utf-8",
                )
                tmp.replace(path)
            except OSError:
                logger.exception(
                    "eventbus-writer: kunne ikke skrive dead-letter-resten tilbage"
                )

            self._drained_total += skrevet
            return skrevet

    def _maaske_drain(self) -> None:
        """Forsøg genindlæsning — kun når køen er tom, og højst hvert minut."""
        nu = time.monotonic()
        if nu - self._last_drain_attempt < _DRAIN_INTERVAL_SECS:
            return
        self._last_drain_attempt = nu
        try:
            path = self._dead_letter_path()
            if not path.exists() or path.stat().st_size == 0:
                return
        except OSError:  # ingen fil eller stat — der er intet at dræne
            return
        try:
            antal = self._drain_dead_letter()
        except Exception:
            logger.exception("eventbus-writer: drain af dead-letter fejlede")
            return
        if antal:
            logger.info("eventbus-writer: genindlæste %d spillede events fra disk", antal)

    def dead_letter_stats(self) -> dict[str, Any]:
        """Tællere + filstørrelse — så «taber vi events?» er et tal, ikke en eftersøgning."""
        path = self._dead_letter_path()
        try:
            pending = path.stat().st_size if path.exists() else 0
        except OSError:
            pending = 0
        return {
            "spilled_total": self._spilled_total,
            "drained_total": self._drained_total,
            "pending_bytes": pending,
            "file": str(path),
        }

    def _write_event(self, item: dict[str, Any]) -> None:
        """Backward-compat single-event wrapper (tests/callers)."""
        self._write_events_batch([item])

    def _write_events_batch(self, batch: list[dict[str, Any]]) -> None:
        """Write a FIFO batch of events in ONE transaction (single commit), then
        notify subscribers per-event after commit. Collapses N commits into 1 →
        fewer WAL write-lock acquisitions under bursts."""
        if not batch:
            return
        written: list[tuple[dict[str, Any], int]] = []
        with connect() as conn:
            for item in batch:
                cursor = conn.execute(
                    """
                    INSERT INTO events (kind, payload_json, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (item["kind"], item["payload_json"], item["created_at"]),
                )
                event_id = int(cursor.lastrowid)
                self._noter_egen(event_id)

                # Write causal edges. Best-effort — never let edge-write
                # break event publication.
                caused_by = item.get("caused_by")
                if caused_by is not None:
                    edge_kind = item.get("edge_kind", "triggered")
                    parents = caused_by if isinstance(caused_by, list) else [caused_by]
                    for pid in parents:
                        try:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO causal_edges
                                (child_event_id, parent_event_id, edge_kind,
                                 confidence, source, created_at, reasoning)
                                VALUES (?, ?, ?, 1.0, 'explicit', ?, '')
                                """,
                                (event_id, int(pid), edge_kind, item["created_at"]),
                            )
                        except Exception:
                            pass
                written.append((item, event_id))
            conn.commit()  # ONE commit for the whole batch

        # Notify subscribers *after* the write is committed so their
        # on-read queries see the event.  put_nowait is non-blocking.
        for item, event_id in written:
            serialized = self._serialize_event(
                event_id=event_id,
                event_kind=item["kind"],
                event_payload=item["payload"],
                created_at=item["created_at"],
            )
            self._notify_subscribers(serialized)

    # ---- Krydsproces --------------------------------------------------

    def _noter_egen(self, event_id: int) -> None:
        with self._egne_lock:
            if len(self._egne_ids) == self._egne_ids.maxlen:
                self._egne_set.discard(self._egne_ids[0])
            self._egne_ids.append(event_id)
            self._egne_set.add(event_id)

    def er_egen(self, event_id: int) -> bool:
        """Skrev denne proces eventet? (Så har lokale abonnenter allerede fået det.)"""
        with self._egne_lock:
            return event_id in self._egne_set

    # ---- Internal helpers ---------------------------------------------

    def _notify_subscribers(self, item: dict[str, Any]) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(item)
            except Exception:
                pass  # a slow subscriber should not stall the bus

    def _serialize_event(
        self,
        *,
        event_id: int,
        event_kind: str,
        event_payload: dict[str, Any],
        created_at: str,
    ) -> dict[str, Any]:
        payload_json = json.dumps(event_payload, ensure_ascii=False)
        family = event_kind.split(".", 1)[0]
        return {
            "id": event_id,
            "kind": event_kind,
            "family": family,
            "payload": event_payload,
            "payload_json": payload_json,
            "created_at": created_at,
        }

    def _deserialize_row(
        self,
        *,
        event_id: int,
        kind: str,
        payload_json: str,
        created_at: str,
    ) -> dict[str, Any]:
        payload = json.loads(payload_json)
        try:
            event = Event.from_record(
                kind=kind,
                payload=payload,
                created_at=created_at,
            )
        except ValueError:
            return {
                "id": event_id,
                "kind": kind,
                "family": "unknown",
                "payload": payload,
                "payload_json": payload_json,
                "created_at": created_at,
            }
        return self._serialize_event(
            event_id=event_id,
            event_kind=event.kind,
            event_payload=event.payload,
            created_at=created_at,
        )


event_bus = EventBus()
