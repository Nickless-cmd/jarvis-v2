# `core.eventbus` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/eventbus/__init__.py`

_(no top-level classes or functions)_

## `core/eventbus/bus.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `EventBus` | `` | Thread-safe event bus with async SQLite writes. | [src](../../../core/eventbus/bus.py#L27) |
| method | `EventBus.__init__` | `(self)` | — | [src](../../../core/eventbus/bus.py#L45) |
| method | `EventBus.publish` | `(self, kind, payload=…, *, caused_by=…, edge_kind=…)` | Publish an event.  Returns immediately — the actual write is async. | [src](../../../core/eventbus/bus.py#L67) |
| method | `EventBus.flush` | `(self, timeout=…)` | Block until the writer has committed *all* events published so far. | [src](../../../core/eventbus/bus.py#L121) |
| method | `EventBus.stop` | `(self)` | Graceful shutdown: drain the writer thread. | [src](../../../core/eventbus/bus.py#L141) |
| method | `EventBus.recent` | `(self, limit=…)` | — | [src](../../../core/eventbus/bus.py#L149) |
| method | `EventBus.recent_by_family` | `(self, family, *, limit=…)` | — | [src](../../../core/eventbus/bus.py#L170) |
| method | `EventBus.recent_since_id` | `(self, after_id, *, limit=…)` | — | [src](../../../core/eventbus/bus.py#L195) |
| method | `EventBus.subscribe` | `(self)` | — | [src](../../../core/eventbus/bus.py#L217) |
| method | `EventBus.unsubscribe` | `(self, subscriber)` | — | [src](../../../core/eventbus/bus.py#L223) |
| method | `EventBus._writer_loop` | `(self)` | Dedicated thread: pull items from queue, write to SQLite, notify. | [src](../../../core/eventbus/bus.py#L231) |
| method | `EventBus._write_event` | `(self, item)` | Backward-compat single-event wrapper (tests/callers). | [src](../../../core/eventbus/bus.py#L282) |
| method | `EventBus._write_events_batch` | `(self, batch)` | Write a FIFO batch of events in ONE transaction (single commit), then | [src](../../../core/eventbus/bus.py#L286) |
| method | `EventBus._notify_subscribers` | `(self, item)` | — | [src](../../../core/eventbus/bus.py#L339) |
| method | `EventBus._serialize_event` | `(self, *, event_id, event_kind, event_payload, created_at)` | — | [src](../../../core/eventbus/bus.py#L348) |
| method | `EventBus._deserialize_row` | `(self, *, event_id, kind, payload_json, created_at)` | — | [src](../../../core/eventbus/bus.py#L367) |

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
| class | `Event` | `` | — | [src](../../../core/eventbus/events.py#L193) |
| method | `Event.family` | `(self)` | — | [src](../../../core/eventbus/events.py#L199) |
| method | `Event.create` | `(cls, kind, payload=…)` | — | [src](../../../core/eventbus/events.py#L203) |
| method | `Event.from_record` | `(cls, *, kind, payload, created_at)` | — | [src](../../../core/eventbus/events.py#L209) |
| method | `Event.validate` | `(self)` | — | [src](../../../core/eventbus/events.py#L220) |

