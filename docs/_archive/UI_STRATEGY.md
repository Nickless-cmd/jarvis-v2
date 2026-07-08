---
status: forældet
audited: 2026-07-08
ground_truth: "Codebase verification: apps/ui/src no Mission Control components post-b8c98551 (deleted 17.5k lines, 42 files); Composer/ChatTranscript/ApprovalCard live; no voice input (grep -r SpeechRecognition returned empty); no artifact panel in web UI (only in jarvis-desk mobile app); git "
superseded_by: docs/CENTRAL_ABSORBS_EVERYTHING_STRATEGY.md or equivalent Central-CLI architecture doc (file not yet located; should document web-UI-chat-only + Central-TUI pattern)
---
# Jarvis V2 UI Strategy

## Core stack
- React for UI
- modern motion, restrained animation
- one primary front door
- Mission Control as separate but tightly integrated control plane

## Chat view
Must support:
- live streamed assistant replies
- tool/skill activity visibility
- event/activity trace while the LLM works
- attachments
- image uploads
- dictation / voice input
- conversation mode
- artifact/work surface when needed

## Composer
Must support:
- text
- drag/drop files
- image attach
- voice/dictation
- send / stop / interrupt
- approval prompts

## Mission Control
Must support:
- runtime health
- events
- token burn / costs
- heartbeat
- approvals
- channel state
- swarm/council visibility
- memory and reflective subsystem signals
- hardware/body state
