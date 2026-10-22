# Progress files

One file per task: `.agents/progress/<task-id>.md` (for example `T-001-01.md`).

```markdown
# T-001-01 progress
**Objective:** <one sentence from tasks.md>
**Status:** in progress | blocked | ready for review
## Done
- <what is finished, with file names>
## Pending
- <what is left>
## Decisions
- <choice made and why>
## Blockers / questions for a human
- <anything that needs a decision>
```

Why: a session can be reset, resumed or handed to another agent without losing the thread. Files carry the
context between sessions; chat history does not.
