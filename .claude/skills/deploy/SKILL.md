---
name: deploy
description: Pre-deployment checklist and release summary. Use when the user
  asks about deploying, releasing, or shipping to any environment.
allowed-tools: Read, Bash, Glob
---
Run the pre-deployment checklist:

1. Summarize commits since last release: `git log --oneline $(git describe --tags --abbrev=0)..HEAD`
2. Confirm tests pass: `npm run test`
3. Confirm lint is clean: `npm run lint`
4. Check for any `.env` changes that need to be applied in the target environment
5. List any DB migrations that need to run

Report a go/no-go recommendation with reasoning.
