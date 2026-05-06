---
description: Run pre-deploy checks and summarize what will be released
argument-hint: [environment]
---
## Pre-Deploy Checklist for $ARGUMENTS

!`git log main...HEAD --oneline`

!`make test`

!`make lint`

Summarize:
1. What commits are included in this release
2. Whether tests and lint passed
3. Any concerns before deploying to $ARGUMENTS
