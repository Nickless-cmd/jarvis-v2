# Spec: Unified Proactive Notification Routing with Device Awareness

**Status:** Draft
**Author:** Jarvis
**Date:** 2026-06-20
**Depends on:** `device_presence`, `proactive_router`, `push_dispatcher`, `recurring_tasks`, `wakeup_dispatcher`, `action_router`

---

## 1. Problem

Proactive notifications (morgenbriefing, reach_out, reminders, wakeups, team invites) are routed through **5 different code paths** with no shared logic:

| Component | Channel decision | Device awareness |
|---|---|---|
| `recurring_tasks` | None — fires blindly into autonomous run | ❌ |
| `wakeup_dispatcher` | Hardcoded `channel="app"` default | ❌ |
| `action_router._reach_out()` | Hardcoded to `ntfy` | ❌ |
| `proactive_router` | Uses `device_presence.rank()` | ⚠️ Only active pings, ignores registered FCM tokens |
| `push_dispatcher` | FCM-blast to all tokens | ⚠️ Knows tokens but not context |

**Result:** Morgenbriefing lands in Discord even when the user is on their phone. Team invites go to desktop queue when the user is on mobile. Reminders go to ntfy even when the user is actively in the app. No user choice. No device awareness.

---

## 2. Goals

1. **User can choose** where proactive notifications land — globally or per-type
2. **Device awareness** that knows ALL registered devices, not just active pings
3. **One routing function** that all components call — no more 5 different paths
4. **Graceful fallback** — if preferred channel is unavailable, fall to next best
5. **Quiet hours** — suppress non-critical notifications during configured hours

---

## 3. Architecture

### 3.1. Notification Preferences (per-user)

New SQLite table `notification_preferences`:

```sql
CREATE TABLE notification_preferences (
    user_id      TEXT PRIMARY KEY,
    global       TEXT DEFAULT 'auto',       -- auto | app | push | discord | telegram
    briefing     TEXT DEFAULT NULL,         -- override for morgenbriefing
    reminder     TEXT DEFAULT NULL,         -- override for reminders
    reach_out    TEXT DEFAULT NULL,         -- override for reach_out
    team_invite  TEXT DEFAULT NULL,         -- override for team invites
    wakeup       TEXT DEFAULT NULL,         -- override for wakeups
    quiet_start  TEXT DEFAULT '23:00',      -- quiet hours start (HH:MM)
    quiet_end    TEXT DEFAULT '07:00',      -- quiet hours end (HH:MM)
    updated_at   TEXT
);
```

**Channel values:**
- `auto` — device awareness decides (default)
- `app` — deliver in jarvis-desk / mobile app (in-app notification + chat message)
- `push` — FCM push notification only (no chat message)
- `discord` — Discord DM
- `telegram` — Telegram message

**Resolution priority:** type-specific override → global → `auto`

### 3.2. Device Awareness (expanded `device_presence.rank()`)

`rank()` currently only considers active presence pings. It must also know about **registered devices**:

| Source | Signal | Current | After |
|---|---|---|---|
| FCM tokens (`device_tokens`) | Mobile registered | ❌ Ignored | ✅ Score 50 if token exists, boosted to 150 if recent ping |
| Desktop sessions | Desktop active | ✅ Via presence ping | ✅ Unchanged |
| Discord gateway | Discord online | ❌ Not checked | ✅ Score 100 if gateway reports user online |
| Telegram | Always available | ❌ Not checked | ✅ Score 30 (low — Telegram is async) |

**Updated `rank()` logic:**
```
1. Collect all presence pings (existing)
2. Query device_tokens for registered FCM tokens → add as candidates
3. Check discord_gateway for user online status → add as candidate
4. Telegram → always add as low-priority candidate
5. Score each candidate:
   - Active ping in last 5 min: score = 200 (highest)
   - Active ping in last 30 min: score = 100
   - Active ping in last 2h: score = 50
   - Registered FCM token, no recent ping: score = 50
   - Discord online: score = 100
   - Telegram: score = 30
6. Return ranked list (highest first)
```

This ensures `rank()` **always returns at least one candidate** if the user has any registered device — no more empty rankings.

### 3.3. Unified Route Function

New function `route_proactive_notification()` in a new module `core/services/notification_router.py`:

```python
def route_proactive_notification(
    user_id: str,
    notification_type: str,   # "briefing" | "reminder" | "reach_out" | "team_invite" | "wakeup" | "general"
    payload: dict,            # {title, body, preview, kind, ...}
    importance: str = "normal",  # "low" | "normal" | "high" | "critical"
) -> dict:
    """
    Unified routing for all proactive notifications.
    Returns {delivered: bool, channel: str, target: str, fallback_used: bool}.
    """
```

**Flow:**

```
1. Load notification_preferences for user_id
   → resolve preferred channel (type-specific → global → "auto")

2. If preferred == "auto":
   → Call device_presence.rank(user_id) [now expanded]
   → Pick highest-scored device
   → Map device to channel:
     - mobile/fcm → "push" (or "app" if app session is active)
     - desktop → "app"
     - discord → "discord"
     - telegram → "telegram"

3. Check quiet hours:
   → If within quiet hours AND importance != "critical":
     → Queue for delivery at quiet_end
     → Return {delivered: False, channel: "queued", reason: "quiet_hours"}

4. Deliver to chosen channel:
   → "app": enqueue in desktop_notifications + trigger in-app notification
   → "push": send via FCM with notification block
   → "discord": send_dm_to_user via discord_gateway
   → "telegram": send_telegram_message

5. Fallback on delivery failure:
   → If chosen channel fails, try next-best from rank()
   → If all fail, fall back to ntfy (last resort)
   → Log delivery attempt in proactive_log
```

### 3.4. Component Integration

Each component is updated to call `route_proactive_notification()` instead of its own routing:

| Component | Before | After |
|---|---|---|
| `recurring_tasks._fire_due()` | `start_autonomous_run(session_id=None)` | Check preferences → route to chosen channel → autonomous run lands in correct session |
| `wakeup_dispatcher` | Hardcoded `channel="app"` | Call `route_proactive_notification(type="wakeup")` |
| `action_router._reach_out()` | Hardcoded to `ntfy` | Call `route_proactive_notification(type="reach_out")` |
| `team_tools.exec_invite_to_team()` | Calls `proactive_router.route()` directly | Call `route_proactive_notification(type="team_invite")` |
| `push_dispatcher.send_answer_push()` | Direct FCM send | Use expanded `device_presence.rank()` to pick device, bypass preferences/quiet hours (reactive, not proactive) |

### 3.5. Recurring Tasks: Channel Field

Add `channel` column to `recurring_tasks` table:

```sql
ALTER TABLE recurring_tasks ADD COLUMN channel TEXT DEFAULT 'auto';
```

When a recurring task fires:
1. Read `channel` from the task row
2. If `auto` → use `route_proactive_notification(type="briefing")`
3. If explicit (`app`, `discord`, `telegram`, `push`) → route directly to that channel
4. Autonomous run's session is selected based on the chosen channel:
   - `app` → owner's app session
   - `discord` → owner's Discord session (if gateway connected)
   - `telegram` → telegram session
   - `push` → no autonomous run, just push notification

---

## 4. API Surface

### 4.1. Tool: `set_notification_preferences`

Visible-lane tool for users to set their preferences:

```python
def exec_set_notification_preferences(args: dict) -> dict:
    """
    Set per-user notification preferences.
    Args: global, briefing, reminder, reach_out, team_invite, wakeup,
          quiet_start, quiet_end
    Each channel value: auto | app | push | discord | telegram
    """
```

### 4.2. Tool: `get_notification_preferences`

Read current preferences for the user.

### 4.3. Tool: `set_recurring_channel`

Set channel on a specific recurring task:

```python
def exec_set_recurring_channel(args: dict) -> dict:
    """
    Set delivery channel for a recurring task.
    Args: task_id, channel (auto | app | push | discord | telegram)
    """
```

---

## 5. Migration Plan

### Phase 1: Device Awareness (backend, no UI)
- Expand `device_presence.rank()` to include FCM tokens + Discord status
- Ensure `rank()` always returns ≥1 candidate if any device is registered
- Test: Mikkel (only FCM) should rank mobile/fcm at score 50 minimum

### Phase 2: Notification Router (backend)
- Create `core/services/notification_router.py`
- Implement `route_proactive_notification()`
- Create `notification_preferences` table + CRUD functions
- Wire `action_router._reach_out()` to new router
- Wire `wakeup_dispatcher` to new router
- Wire `team_tools.exec_invite_to_team()` to new router

### Phase 3: Recurring Tasks
- Add `channel` column to `recurring_tasks`
- Update `_fire_due()` to use `route_proactive_notification(type="briefing")`
- Add `set_recurring_channel` tool

### Phase 4: User-facing Tools
- Add `set_notification_preferences` + `get_notification_preferences` tools
- Add UI in jarvis-desk settings (note for Claude)
- Add UI in mobile app settings (note for Claude)

### Phase 5: Cleanup
- Remove old hardcoded routing from `push_dispatcher.send_answer_push()`
- Remove old `proactive_router.route()` (replaced by notification_router)
- Remove `_fallback_blast()` (replaced by unified fallback in notification_router)

---

## 6. Edge Cases

- **No devices registered at all** → Fall back to ntfy (last resort, always works)
- **User offline on all channels** → Queue in desktop_notifications, deliver on next session open
- **Quiet hours + critical importance** → Deliver immediately, bypass quiet hours
- **Discord gateway disconnected** → Skip Discord, try next in rank
- **FCM token invalid** → Delete token (existing behavior), try next in rank
- **User has no preferences set** → Default to `auto` for everything
- **Multiple FCM tokens** (phone + tablet) → Send to highest-scored one, not all (unlike current blast)

---

## 7. Testing

- `test_notification_router.py` — unit tests for routing logic, quiet hours, fallback
- `test_device_presence.py` — expand to test FCM token + Discord awareness
- `test_recurring_tasks.py` — test channel field + routing
- Integration test: set preferences → trigger briefing → verify it lands on correct channel

---

## 8. Self-Review (2026-06-20)

### Issues found and fixed during review:

1. **`answer_ready` is reactive, not proactive** — `push_dispatcher.send_answer_push()` fires when the user is already waiting for a response. It should NOT go through `route_proactive_notification()`. Instead, it should use the expanded `device_presence.rank()` to pick the right device, but bypass preferences/quiet hours. Removed from component integration table in §3.4.

2. **Quiet hours queuing mechanism unspecified** — Spec said "queue for delivery at quiet_end" without saying how. Resolution: use a `delayed_notifications` SQLite table that stores payload + target time. A poller checks for due delayed notifications and fires them via `route_proactive_notification()` (bypassing quiet hours since they're already past).

3. **`device_tokens` filtering** — `rank()` must filter FCM tokens by `user_id`. `device_tokens.list_for_user(user_id)` already does this — the expanded `rank()` must call it with the correct user_id.

4. **Auto mode mapping ambiguity** — "mobile/fcm → push (or app if app session is active)" clarified: if `rank()` returns mobile AND there's an active app session for the same user, deliver to `app` (in-app notification + chat). If only mobile FCM token (no active app session), deliver to `push` (notification only, no chat message).

5. **Session selection for autonomous runs** — clarified in §3.5: when `channel="app"`, use `resolve_owner_app_session()`. When `channel="discord"`, use owner's Discord session if gateway connected, else fallback. When `channel="push"`, no autonomous run — just push the notification.

### Confirmed correct:
- Migration phases are correctly ordered (Phase 1 device awareness → Phase 2 router → Phase 3 recurring tasks → Phase 4 UI → Phase 5 cleanup)
- Edge cases cover the main failure modes
- Per-user preferences (not per-contact) is the right granularity
- `proactive_router` can be fully replaced by `notification_router` after all components are wired

---

## 9. Open Questions

1. **Should `auto` prefer the device with the most recent activity, or the one the user is currently looking at?** (Current proposal: most recent activity wins)
2. **Should morgenbriefing create a chat message in the app, or just a push notification?** (Current proposal: if `app`, create chat message; if `push`, only notification)
3. **Should Telegram be a first-class channel or just a fallback?** (Current proposal: first-class, but low priority in auto mode)
4. **Should we allow per-contact preferences (e.g., Mikkel gets Discord, Bjørn gets app)?** (Current proposal: yes, it's per-user)