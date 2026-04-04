# HEARTBEAT

Status: enabled
Interval Minutes: 15
Allow Propose: true
Allow Execute: true
Allow Ping: true
Ping Channel: webchat
Budget: bounded-internal-only
Kill Switch: enabled

Heartbeat exists to keep Jarvis temporally present in a bounded way.
It may notice due loops, produce proposals, and record a ping preview when policy allows.
It must not create silent writes, destructive actions, or uncontrolled outward behavior.
