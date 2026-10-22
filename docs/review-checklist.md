# Reviewing code you did not write

Use this on every pull request that an agent produced or helped with. The automated gates run first; this is the human part.

1. **Spec fit.** Link to the spec or issue. Which acceptance criteria does the change cover? Does it do that and nothing more, nothing less?
2. **Who wrote it.** Human, agent-assisted or agent-delegated? Model and accountable operator named in the commit trailers?
3. **Gates are green.** Tests, lint, secrets scan, dependency check, mutation score, traceability. Do not review red builds.
4. **Scope.** Did the diff touch only the files the task allowed? Any unrequested file, permission, CI or config change is a finding.
5. **Tests assert behaviour.** Not just status codes. Would a mutated line fail them? Does a bug fix have a regression test that fails without the fix? Anything skipped, deleted or weakened?
6. **Data and secrets.** No personal data, secrets or health information in code, logs, error text, messages or test fixtures.
7. **Injection and safety.** SQL built from strings, shell commands from input, new network calls, new dependencies (license, age, maintainer).
8. **Risk tier.** Authentication, personal data, payments, **migrations**, infrastructure, permissions are High: a second reviewer and a short security note.
9. **Agent review findings.** Every finding is fixed or dismissed with a written reason. The person who prompted the agent is never the only approver.
10. **Decision.** Approve, request changes, or block. Agents never merge.
