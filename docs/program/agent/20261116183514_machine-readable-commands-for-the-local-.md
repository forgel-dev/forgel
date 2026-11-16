# Agent Run: Machine-readable commands for the local client

- Task: `20261116183514_machine-readable-commands-for-the-local-`
- Status: `done`
- Repository: `main`
- Steps: 58
- Finished: 2026-11-16T19:57:05+00:00

## Requirements

- Every operation the local client shows must be reachable as a parameterized `forgel` subcommand that needs no interactive prompt: free text, project status, milestone status, task list, accept a task, reject a task, retry a task, run the daemon now, pause, resume, plan a milestone from a goal, list projects, select the active project.
- Free text sent by the user must have a single engine entry point (`forgel say`) that returns the same structured outcome as the chat router: an answer, a queued task, a plan, or a control action, with the reply text.
- Each of those subcommands must accept `--json` and then write exactly one JSON object to stdout and nothing else; without the flag the existing human-readable text stays the output.
- The JSON object must carry a stable envelope: a success flag, a kind, the reply text and the operation-specific payload; a failed call must exit with a non-zero status and still return one JSON object describing the error.
- The active project must be a durable session on the engine side, addressable by a session key that defaults to `local`, so the client stays stateless between calls. Commands to set and read the session are required.
- Free text must go through the same router logic that console and Telegram use; no duplicated dispatch table and no second implementation of the same command in the CLI layer.
- The recent conversation of a session must be readable as a command that returns it in JSON, so the client can show a short history without reading project files.
- Existing behaviour must not change: `forgel chat`, `forgel telegram`, `forgel`, the interactive commands and their texts keep working as before, and the existing test suite stays green.
- Document the command set and the JSON envelope in the public docs (README and the relevant section of PLAN.md) so the future client repository can rely on a written contract.
- Add `unittest` tests that assert the JSON envelope for each new command, the error envelope and exit codes, and that `forgel say` routes a change request to a queued task in script model mode.

## Acceptance Criteria

- `python3 -m unittest discover -s tests` passes and includes new tests for the command interface.
- Each new subcommand with `--json` prints exactly one JSON object and exits 0 on success, verified by a test.
- A failing call exits non-zero and prints one JSON object with an error description, verified by a test.
- With script model mode, `forgel say --project <id> --json --text "add a health endpoint"` returns a JSON object with kind `change_request` and the queued task id, verified by a test.
- `forgel status <id> --json`, `forgel tasks <id> --json`, `forgel task accept --json`, `forgel task reject --json`, `forgel task retry --json`, `forgel plan --status --json` and `forgel projects --json` are covered by tests and documented.
- The session commands set and read the active project for a session key and default to `local`, covered by a test.
- Existing console and Telegram tests still pass unchanged.

## Constraints

- Do not move the console yet and do not delete the chat mode in this task; that is the next step.
- Do not let the CLI layer reimplement routing: it must call the existing router and core functions.
- No new third-party dependencies.
- Public artifacts (docs, commit messages, code identifiers) in English, commits signed off.
- The JSON envelope must be documented, not just implemented, and must not leak secrets.

## Assumptions

- The session key defaults to `local`, matching the console's chat id 0, and is passed with `--session` when another value is needed.
- The free-text entry point is named `forgel say` and takes the text with `--text` (or as the trailing argument) plus `--project`.
- With `--json`, stdout carries only the JSON object; human text goes to stdout only without the flag.
- The envelope is flat at the top level: `ok`, `kind`, `text`, `error`, plus an operation-specific field such as `task`, `tasks`, `plan`, `project`, `projects` or `history`.
- The work stays in the `main` repository; the client repository is created in the following step.
- Без `--json` ошибка пишется только в stderr (как в остальном CLI), а stdout остаётся пустым — так человекочитаемый режим не смешивается с JSON.
- Для ранее существовавших команд (`status`, `task`, `plan`, `pause`, `resume`, `daemon`) клиент перехватывает управление только при наличии `--json`, поэтому их прежний вывод не изменился.
- Документация продублирована в README и PLAN.md, а docs/program/commands.md остаётся полным письменным контрактом для будущего клиентского репозитория.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 58
- Estimated input tokens (all calls): 3346218
- Provider input/output tokens: 3456466 / 136571
- Estimated prompt at the end: 97907 tokens
- State: not needed

## Summary

Доработал предыдущую реализацию по двум замечаниям ревью.

1. Флаг `--json` теперь действительно управляет выводом. В `src/forgel/client_cli.py` добавлены `emit()` и `fail()`: с `--json` в stdout уходит ровно один JSON-объект, без флага печатается человекочитаемый `text` (для ошибок — сообщение в stderr, stdout пустой). Хелперы применены во всех командах — say, projects, session, use, history, tasks, status, task, plan, pause, resume, daemon; `write()` остался только для внутреннего вывода конверта.
2. Публичная документация обновлена. В README.md появился раздел «Scripted Client» с набором команд и таблицей конверта (и ссылка из «One Client»), в PLAN.md добавлен раздел §7.18 «Machine-Readable Client Commands» с конвертом, правилами `say`, сессиями и совместимостью; docs/program/commands.md приведён к тому же контракту.

Новые тесты в tests/test_client.py: `test_without_json_the_human_readable_text_is_printed` (tasks/projects/say/session/history без флага печатают текст, а не JSON) и `test_failing_call_without_json_prints_no_object` (ошибка без флага — ненулевой код и пустой stdout). Остальные тесты предыдущей итерации (конверт каждой команды, ошибка с одним JSON и ненулевым кодом, сессии с ключом по умолчанию `local`, история, `say` с маршрутизацией `change_request` в очередь в script-режиме) сохранены. Полный прогон `python3 -m unittest discover -s tests` — 529 тестов, OK, включая существующие console/Telegram тесты без изменений.

## Files Changed

- `PLAN.md`
- `README.md`
- `src/forgel/client_cli.py`
- `tests/test_client.py`
- `tests/test_tmp_size.py`
- `tools/plan_commands.py`

## Commands

- `["python3", "-m", "unittest", "tests.test_client"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_tmp_size.py", "-v"]` → exit 0
- `["python3", "tools/plan_commands.py"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261116195602_inspect-and-finish: context handoff to session 2 (~4816/3072 tokens)
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
....................................................error: unknown project 'missing-project'
..error: unknown project 'missing-project'
.......error: say needs text: --text "..." or a trailing argument
....................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 529 tests in 76.488s

OK

```

## Actions

- read_file: src/forgel/client.py
- read_file: src/forgel/client_cli.py
- read_file: tests/test_client.py
- read_file: src/forgel/entry.py
- read_file: docs/program/commands.md
- read_file: README.md
- read_file: src/forgel/outcome.py
- read_file: PLAN.md
- read_file: PLAN.md
- read_file: PLAN.md
- read_file: src/forgel/cli.py
- read_file: PLAN.md
- read_file: PLAN.md
- read_file: PLAN.md
- read_file: src/forgel/cli.py
- write_file: src/forgel/client_cli.py
- write_file: tests/test_client.py
- run: ['python3', '-c', 'import pathlib\n\nreadme = pathlib.Path(\'README.md\')\nt = readme.read_text(encoding=\'utf-8\')\nold = \'- Every console command also exists as `forgel <command>` for scripts.\'\nassert old in t\nt = t.replace(old, \'- Every console command also exists as a `forgel` subcommand for scripts,\\n  with `--json` for one machine-readable object per call (see\\n  [Scripted Client](#scripted-client)).\', 1)\nsection = \'\'\'## Scripted Client\n\nEvery operation the local client shows is also a `forgel` subcommand that never\nprompts. Add `--json` and stdout carries exactly one JSON object and nothing\nelse; without the flag the human-readable text is printed as before.\n\n```bash\nforgel say --project <id> --text "add a health endpoint" [--json]\nforgel status <id> --json\nforgel tasks <id> --json\nforgel task accept|reject|retry --project <id> --task <id> --json\nforgel plan <id> --status --json\nforgel plan <id> --goal "ship M1" [--dry-run] --json\nforgel projects --json\nforgel session [<id>] [--session <key>] --json\nforgel use <id> [--session <key>] --json\nforgel history [--session <key>] [--limit N] --json\nforgel daemon [--once|--loop] [--interval S] [--max-cycles N] --json\nforgel pause --json\nforgel resume --json\n```\n\nThe envelope is flat: `ok` (success flag), `kind`, `text` (the reply text),\n`error` (empty on success) plus one operation-specific field such as `task`,\n`tasks`, `plan`, `project`, `projects`, `history`, `paused` or `cycles`. A\nfailed call exits non-zero and still returns one JSON object with "ok": false\nand the reason in `error`. `forgel say` is the single free-text entry point and\nreports what the message became — an `answer`, a `change_request` with the\nqueued task, a `plan` or a control `action` — through the same router the\nconsole and Telegram use. The active project is a durable engine-side session\naddressed by `--session` and defaulting to `local`, so the client keeps no\nstate between calls. The full command set and contract are in\n[docs/program/commands.md](docs/program/commands.md).\n\n\'\'\'\nanchor = \'## Try the M0 Skeleton\'\nassert anchor in t\nt = t.replace(anchor, section + anchor, 1)\nreadme.write_text(t, encoding=\'utf-8\')\n\nplan = pathlib.Path(\'PLAN.md\')\np = plan.read_text(encoding=\'utf-8\')\nanchor2 = \'\\n---\\n\\n## 8. Gates\\n\'\nassert anchor2 in p\nplan_section = \'\'\'### 7.18 Machine-Readable Client Commands\n\nThe local client is a thin shell over the engine, so every operation it shows\nis reachable as a parameterized `forgel` subcommand that needs no interactive\nprompt: `say`, `status`, `tasks`, `task accept|reject|retry`, `plan`,\n`projects`, `session`, `use`, `history`, `daemon`, `pause` and `resume`. Each\naccepts `--json`.\n\nThe envelope is stable and flat: `ok` (success flag), `kind`, `text` (the reply\ntext), `error` (empty on success) plus one operation-specific field such as\n`task`, `tasks`, `plan`, `project`, `projects` or `history`. With `--json`\nstdout carries exactly one JSON object and nothing else; without the flag the\nhuman-readable text stays. A failed call exits non-zero and still writes one\nJSON object with `"ok": false` and the reason in `error`. Payloads never carry\nsecrets.\n\n`forgel say --text "..." [--project <id>]` is the only free-text entry point\nand returns the same structured outcome the console and Telegram receive from\n`CommandRouter` — an answer, a queued change request with its task id, a plan\nor a control action — so the CLI layer has no dispatch table of its own. The\nactive project is a durable engine-side session addressed by `--session`\n(default `local`, the console\'s chat id 0): `forgel session <project>` sets it,\n`forgel session` reads it, and `forgel history` returns the recent\nconversation as JSON, so the client stays stateless between calls. The written\ncontract is `docs/program/commands.md`.\n\n\'\'\'\np = p.replace(anchor2, \'\\n\' + plan_section + \'---\\n\\n## 8. Gates\\n\', 1)\nplan.write_text(p, encoding=\'utf-8\')\nprint(\'docs updated\')']
- read_file: PLAN.md
- run: ['python3', '-m', 'unittest', 'tests.test_client']
- run: ['python3', '-c', "import pathlib\nroot = pathlib.Path('.')\ncommands = (root / 'docs' / 'program' / 'commands.md').read_text(encoding='utf-8')\nreadme_section = commands.replace('# Machine-readable client commands', '## Scripted Client', 1).replace('\\n## ', '\\n### ')\nreadme = root / 'README.md'\ntext = readme.read_text(encoding='utf-8')\nanchor = '## Try the M0 Skeleton'\nassert text.count(anchor) == 1\nreadme.write_text(text.replace(anchor, readme_section + '\\n' + anchor, 1), encoding='utf-8')\nplan_section = commands.replace('# Machine-readable client commands', '### 7.18 Machine-Readable Client Commands', 1).replace('\\n## ', '\\n#### ')\nplan = root / 'PLAN.md'\nplan_text = plan.read_text(encoding='utf-8')\nplan_anchor = '\\n---\\n\\n## 8. Gates\\n'\nassert plan_text.count(plan_anchor) == 1\nplan.write_text(plan_text.replace(plan_anchor, '\\n' + plan_section + '\\n---\\n\\n## 8. Gates\\n', 1), encoding='utf-8')\nprint('docs updated')"]
- write_file: README.md
- run: ['wc', '-c', 'PLAN.md']
- write_file: tests/test_tmp_size.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_tmp_size.py', '-v']
- read_file: Makefile
- read_file: PLAN.md
- run: ['python3', '-c', 'import pathlib\nsection = """\n---\n\n## 15. Machine-Readable Client Commands\n\nThe local client is a thin shell over the engine, so every operation it shows is\nalso a parameterized `forgel` subcommand that never prompts. The set is `say`,\n`status`, `tasks`, `task accept|reject|retry`, `plan` (with `--goal` or\n`--status`), `projects`, `session`, `use`, `history`, `daemon`, `pause` and\n`resume`; each accepts `--json`. The command surface is defined by\n`src/forgel/client.py` and implemented by `src/forgel/client_cli.py`.\n\n**Envelope.** The JSON object is flat and stable: `ok` (success flag), `kind`,\n`text` (the reply text a human would see) and `error` (empty on success), plus\none operation-specific field — `task` (and `task_id`), `tasks`, `plan`,\n`project`, `projects`, `history`, `paused` or `cycles`. With `--json` stdout\ncarries exactly one JSON object and nothing else; without the flag the\nhuman-readable text is the output, unchanged from before. A failed call exits\nwith a non-zero status and still writes one JSON object with `\\"ok\\": false`\nand the reason in `error`; the same reason goes to stderr. Payloads never carry\nsecrets.\n\n**Free text.** `forgel say --text \\"...\\" [--project <id>] [--session <key>]`\nis the single free-text entry point. It calls the same `CommandRouter` the\nconsole and Telegram use (through `src/forgel/outcome.py`) and returns the same\nstructured outcome: an `answer`, a `change_request` with the queued task id, a\n`plan` or a control `action`, together with the reply text. The CLI layer holds\nno dispatch table of its own.\n\n**Sessions.** The active project is a durable engine-side session, so the\nclient keeps no state between calls. The session key defaults to `local` (the\nconsole\'s chat id 0) and is chosen with `--session`; `forgel session <project>`\nand `forgel use <project>` set it, `forgel session` reads it back, `forgel\nprojects` marks the selected one, and `forgel history` returns the recent\nconversation of the session as JSON, so the client can show a short history\nwithout reading project files.\n\n**Compatibility.** `forgel chat`, `forgel telegram`, bare `forgel` and their\ninteractive commands keep working unchanged; `status`, `task`, `plan`,\n`pause`, `resume` and `daemon` are taken over by the client only when `--json`\nis given. The written contract for the future client repository is\n`docs/program/commands.md`.\n"""\npath = pathlib.Path(\'PLAN.md\')\nwith path.open(\'a\', encoding=\'utf-8\') as handle:\n    handle.write(section)\nprint(\'PLAN.md updated\')']
- delete_file: tests/test_tmp_size.py
- read_file: PLAN.md
- read_file: PLAN.md
- run: ['python3', '-c', 'import io\nsection = \'\'\'\n---\n\n## 15. Machine-Readable Client Commands\n\nThe local client is a thin shell over the engine, so every operation it shows is\nalso a parameterized `forgel` subcommand that never prompts: `say`, `status`,\n`tasks`, `task accept|reject|retry`, `plan` (with `--goal` or `--status`),\n`projects`, `session`, `use`, `history`, `daemon`, `pause` and `resume`. Each\naccepts `--json`; the parser lives in `src/forgel/client.py` and the commands in\n`src/forgel/client_cli.py`.\n\n**Envelope.** The JSON object is flat and stable: `ok` (success flag), `kind`,\n`text` (the reply text a human would see) and `error` (empty on success), plus\none operation-specific field -- `task` (with `task_id`), `tasks`, `plan`,\n`project`, `projects`, `history`, `paused` or `cycles`. With `--json` stdout\ncarries exactly one JSON object and nothing else; without the flag the\nhuman-readable text is the output, unchanged from before. A failed call exits\nnon-zero and still writes one JSON object with `ok: false` and the reason in\n`error`; the same reason goes to stderr. Payloads never carry secrets.\n\n**Free text.** `forgel say --text \\"...\\" [--project <id>] [--session <key>]`\nis the single free-text entry point. It calls the same `CommandRouter` the\nconsole and Telegram use (observed by `src/forgel/outcome.py`) and returns the\nsame structured outcome: an `answer`, a `change_request` with the queued task\nid, a `plan` or a control `action`, together with the reply text. The CLI layer\nholds no dispatch table of its own.\n\n**Sessions.** The active project is a durable engine-side session, so the client\nkeeps no state between calls. The session key defaults to `local` (the console\nchat id 0) and is chosen with `--session`; `forgel session <project>` and\n`forgel use <project>` set it, `forgel session` reads it back, `forgel projects`\nmarks the selected one, and `forgel history` returns the recent conversation of\nthe session as JSON, so a client can show a short history without reading\nproject files.\n\n**Compatibility.** `forgel chat`, `forgel telegram`, bare `forgel` and their\ninteractive commands keep working unchanged; `status`, `task`, `plan`, `pause`,\n`resume` and `daemon` are taken over by the client only when `--json` is given.\nThe written contract for the future client repository is\n`docs/program/commands.md`.\n\'\'\'\nhandle = io.open(\'PLAN.md\', \'a\', encoding=\'utf-8\')\nhandle.write(section)\nhandle.close()\nprint(\'PLAN.md updated\')']
- read_file: PLAN.md
- write_file: tools/plan_commands.py
- run: ['python3', 'tools/plan_commands.py']
- read_file: PLAN.md
- delete_file: tools/plan_commands.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: README.md
- read_file: README.md
