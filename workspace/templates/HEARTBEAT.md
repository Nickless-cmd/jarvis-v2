# HEARTBEAT

Status: enabled
Interval Minutes: 180
Allow Propose: true
Allow Execute: false
Allow Ping: false
Ping Channel: none
Budget: bounded-internal-only
Kill Switch: enabled

Heartbeat exists to keep Jarvis temporally present in a bounded way.
It may notice due loops, produce proposals, and record a ping preview when policy allows.
It must not create silent writes, destructive actions, or uncontrolled outward behavior.
