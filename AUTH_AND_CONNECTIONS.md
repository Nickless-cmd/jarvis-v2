# Auth and Connections

## Required first-class connections
- GitHub
- Codex/OpenAI auth
- workspace/profile-scoped credentials

## Rules
- UI session auth is separate from provider OAuth
- no secrets in repo
- credentials live in runtime state dir
- all connections are observable in Mission Control
- revoke/rotate must be supported

## Future
- additional providers may be added under same auth profile model
