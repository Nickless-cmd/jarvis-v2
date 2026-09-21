# `core.eventbus` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/eventbus/__init__.py`

_(no top-level classes or functions)_

## `core/eventbus/bus.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `EventBus` | `` | Thread-safe event bus with async SQLite writes. | [src](../../../core/eventbus/bus.py#L31) |
| method | `EventBus.__init__` | `(self)` | — | [src](../../../core/eventbus/bus.py#L49) |
| method | `EventBus.publish` | `(self, kind, payload=…, *, caused_by=…, edge_kind=…)` | Publish an event.  Returns immediately — the actual write is async. | [src](../../../core/eventbus/bus.py#L79) |
| method | `EventBus.flush` | `(self, timeout=…)` | Block until the writer has committed *all* events published so far. | [src](../../../core/eventbus/bus.py#L133) |
| method | `EventBus.stop` | `(self)` | Graceful shutdown: drain the writer thread. | [src](../../../core/eventbus/bus.py#L153) |
| method | `EventBus.recent` | `(self, limit=…)` | — | [src](../../../core/eventbus/bus.py#L161) |
| method | `EventBus.recent_by_family` | `(self, family, *, limit=…)` | — | [src](../../../core/eventbus/bus.py#L182) |
| method | `EventBus.recent_since_id` | `(self, after_id, *, limit=…)` | — | [src](../../../core/eventbus/bus.py#L207) |
| method | `EventBus.subscribe` | `(self)` | — | [src](../../../core/eventbus/bus.py#L229) |
| method | `EventBus.unsubscribe` | `(self, subscriber)` | — | [src](../../../core/eventbus/bus.py#L235) |
| method | `EventBus._writer_loop` | `(self)` | Dedicated thread: pull items from queue, write to SQLite, notify. | [src](../../../core/eventbus/bus.py#L243) |
| method | `EventBus._write_event` | `(self, item)` | Backward-compat single-event wrapper (tests/callers). | [src](../../../core/eventbus/bus.py#L294) |
| method | `EventBus._write_events_batch` | `(self, batch)` | Write a FIFO batch of events in ONE transaction (single commit), then | [src](../../../core/eventbus/bus.py#L298) |
| method | `EventBus._noter_egen` | `(self, event_id)` | — | [src](../../../core/eventbus/bus.py#L352) |
| method | `EventBus.er_egen` | `(self, event_id)` | Skrev denne proces eventet? (Så har lokale abonnenter allerede fået det.) | [src](../../../core/eventbus/bus.py#L359) |
| method | `EventBus._notify_subscribers` | `(self, item)` | — | [src](../../../core/eventbus/bus.py#L366) |
| method | `EventBus._serialize_event` | `(self, *, event_id, event_kind, event_payload, created_at)` | — | [src](../../../core/eventbus/bus.py#L375) |
| method | `EventBus._deserialize_row` | `(self, *, event_id, kind, payload_json, created_at)` | — | [src](../../../core/eventbus/bus.py#L394) |

## `core/eventbus/context.py`
_EventContext — ContextVar holding the current parent event_id._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `set_current_event` | `(event_id)` | Set parent-event-id for the current dispatch scope. | [src](../../../core/eventbus/context.py#L22) |
| function | `get_current_event` | `()` | Return current parent-event-id, or None if none active. | [src](../../../core/eventbus/context.py#L31) |
| function | `with_event_context` | `(event_id)` | Context manager that sets and reliably resets EventContext. | [src](../../../core/eventbus/context.py#L37) |

## `core/eventbus/events.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Event` | `` | — | [src](../../../core/eventbus/events.py#L258) |
| method | `Event.family` | `(self)` | — | [src](../../../core/eventbus/events.py#L264) |
| method | `Event.create` | `(cls, kind, payload=…)` | — | [src](../../../core/eventbus/events.py#L268) |
| method | `Event.from_record` | `(cls, *, kind, payload, created_at)` | — | [src](../../../core/eventbus/events.py#L274) |
| method | `Event.validate` | `(self)` | — | [src](../../../core/eventbus/events.py#L285) |

## `core/eventbus/krydsproces.py`
_Krydsproces-relæ: events fra den ANDEN proces når de lokale abonnenter._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `relae_en_gang` | `(bus, sidste_id, *, limit=…)` | Én poll. Returnerer (ny sidste_id, antal leveret). | [src](../../../core/eventbus/krydsproces.py#L44) |
| function | `_nyeste_id` | `(bus)` | — | [src](../../../core/eventbus/krydsproces.py#L57) |
| function | `_loop` | `(bus)` | — | [src](../../../core/eventbus/krydsproces.py#L62) |
| function | `start_relae` | `(bus=…)` | Idempotent. Startes i den proces hvor lytterne bor (runtime). | [src](../../../core/eventbus/krydsproces.py#L73) |

## `core/eventbus/publish_scan.py`
_Find hvert publish-kald med en familie.navn-literal — statisk, uden at koere noget._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_repo_root` | `()` | — | [src](../../../core/eventbus/publish_scan.py#L42) |
| function | `scan_published_families` | `(rod=…)` | familie → liste af "sti:linje" hvor den publiceres. | [src](../../../core/eventbus/publish_scan.py#L46) |
| function | `unregistered_families` | `(rod=…)` | De publicerede familier der IKKE er tilladt → publish raiser tavst. | [src](../../../core/eventbus/publish_scan.py#L77) |
| function | `dict_form_publish_calls` | `(rod=…)` | Find hvert ``X.publish({...})``-kald — dict-formen der ALTID raiser på event_bus. | [src](../../../core/eventbus/publish_scan.py#L88) |

