# Release audit 20261123193557155149_forgel-code-interactive-agent-client-instead-of-

- Round: 6
- Verdict: fail
- At: 2026-11-24T13:11:24+00:00

## Summary

The release implements most of the interactive client and has broad test coverage, but the audit found a blocking authorization gap in sensitive-action detection and an explicit regression in the one-shot CLI help output. The new README also contradicts the implemented plain-sentence behavior.

## Findings

- [major] code: The sensitive-action guard is incomplete for required explicit actions. `SENSITIVE_MARKERS`, `CREDENTIAL_NOUNS`, `CONFIG_NOUNS` and the create/change stems do not cover bare `key`/`ключ`, `config`, or `scaffold`, so free-text requests such as `change config`, `create a key`, `создай ключ`, or `scaffold a project` are not refused and can be sent to the engine as ordinary `say` requests. This violates the requirement that setting key material and changing configuration or creating/scaffolding a project never happen from free text alone. No tests assert no-passthrough for these forms. — Extend sensitive-action detection with verb-plus-object handling for English and Russian, including the missing key, config, and scaffold terms, and add tests that these requests are refused and produce no outgoing engine `say` request while ordinary mentions remain forwarded.
- [major] code: `forgel_code/cli.py` changes the argparse description to include `Run it without a command to open the interactive session.` This changes the output of `forgel-code --help`, an existing non-interactive usage, while the requirements and acceptance say every existing one-shot usage keeps its previous output. The review statement that `--help` output is unchanged is contradicted by the diff. — Restore the original parser description so `forgel-code --help` output is byte-for-byte unchanged; interactive documentation belongs in README/CHANGELOG rather than in existing help output. Keep a test that pins the one-shot help output if the contract requires it.
- [minor] code: The new README section contradicts itself and the documented behavior: the table maps `a plain sentence` to the project agent's answer, but the following paragraph says `A sentence that names no action ... gets a clarification` and nothing is carried out. A plain sentence is exactly a sentence that names no action, so the user is told both that it is answered and that it is not. — Reword the paragraph to say that an action-bearing request that cannot be resolved, such as one missing a task, remarks or project, or one matching several actions, gets a clarification and performs nothing; a plain sentence is forwarded to the agent.
