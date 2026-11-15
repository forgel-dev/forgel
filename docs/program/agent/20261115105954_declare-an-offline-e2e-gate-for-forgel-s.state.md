# Session State: Declare an offline e2e gate for Forgel's own self-hosting pipeline

- Task: `20261115105954_declare-an-offline-e2e-gate-for-forgel-s`
- Session: 3
- Status: in progress

## Goal

Implement the task requirements in the repository, run the final test and
commit. Continue from this state; do not repeat finished work.

## Requirements

- Add an e2e entry to environment.yaml with a command list that runs an offline end-to-end smoke of Forgel on itself: adopt a local fixture repository, plan a milestone with the scripted model, run one task through coding agent, task QA and review, and stop at the staging approval gate.
- The self-hosting e2e must run with FORGEL_MODEL_MODE=script, must not touch the network, Docker or cloud resources, and must finish within a couple of minutes.
- Add tests/e2e/ self-hosting driver (or extend the existing one) that the environment.yaml e2e command invokes and that exits non-zero on a red gate.
- Extend tests/test_environment.py to assert that environment.yaml declares both test and e2e and that the e2e command parses into a non-empty argument list.

## Acceptance Criteria

- The environment test passes with an e2e declaration.
- The self-hosting e2e command exits 0 in the repository sandbox, asserted by the suite run that invokes it.
- The e2e run stops at the staging approval gate and never reaches done without an approval, asserted by the driver.

## Constraints

- No external services, cloud resources or network calls.
- Deterministic output; clean up temporary directories.
- Do not weaken existing tests; keep the suite green.

## Assumptions

- none

## Files Changed

- docs/program/agent/20261115105954_declare-an-offline-e2e-gate-for-forgel-s.state.md
- docs/program/tasks/20261115105954_declare-an-offline-e2e-gate-for-forgel-s.json
- src/forgel/templates/django-drf-react/

## Actions

- read_file: environment.yaml
- read_file: tests/test_environment.py
- read_file: tests/e2e/README.md
- read_file: tests/e2e/run_blog_e2e.py
- read_file: src/forgel/environment.py
- list_files
- run: ['ls', 'tests', 'tests/e2e']
- list_files
- read_file: tests/e2e/blog_actions.py
- read_file: src/forgel/approvals.py
- read_file: src/forgel/daemon.py
- read_file: src/forgel/orchestrator.py
- read_file: src/forgel/planner.py
- read_file: src/forgel/model.py
- run: ['python', '-c', "import os; print('\\n'.join(sorted(os.listdir('tests'))))"]
- read_file: tests/test_e2e.py
- run: ['python', '-c', "import os; print(chr(10).join(sorted(os.listdir('tests/e2e'))))"]
- read_file: src/forgel/task_review.py
- read_file: src/forgel/config.py
- read_file: src/forgel/adopt.py
- read_file: src/forgel/task_qa.py
- read_file: Makefile
- read_file: src/forgel/layout.py
- read_file: docs/program/tasks/20261115105954_declare-an-offline-e2e-gate-for-forgel-s.json
- read_file: src/forgel/tasks.py
- read_file: environment.yaml
- read_file: src/forgel/environment.py
- read_file: tests/test_environment.py
- read_file: tests/e2e/run_blog_e2e.py
- read_file: tests/test_e2e.py
- read_file: src/forgel/orchestrator.py
- read_file: src/forgel/planner.py
- read_file: src/forgel/daemon.py
- read_file: src/forgel/config.py
- list_files
- read_file: tests/e2e/__init__.py
- read_file: src/forgel/model.py
- read_file: src/forgel/adopt.py
- read_file: src/forgel/coding_agent.py
- read_file: src/forgel/task_qa.py
- read_file: src/forgel/approvals.py
- read_file: src/forgel/task_review.py
- read_file: src/forgel/state.py
- read_file: src/forgel/tasks.py
- list_files
- read_file: Makefile
- read_file: docs/program/state.md
- read_file: src/forgel/project_config.py
- list_files
- run: ['python', '-c', "import os; print(chr(10).join(sorted(os.listdir('tests'))))"]
- read_file: tests/e2e/blog_actions.py
- read_file: src/forgel/templates/hello-web/environment.yaml
- read_file: src/forgel/sync.py
- read_file: src/forgel/templates/hello-web/e2e/check.py
- read_file: src/forgel/complexity.py
- read_file: environment.yaml
- read_file: tests/test_environment.py
- read_file: src/forgel/orchestrator.py
- read_file: src/forgel/model.py
- read_file: tests/test_e2e.py
- read_file: src/forgel/planner.py
- read_file: tests/e2e/run_blog_e2e.py
- read_file: docs/program/tasks/20261115105954_declare-an-offline-e2e-gate-for-forgel-s.json
- read_file: src/forgel/daemon.py
- read_file: src/forgel/adopt.py
- read_file: tests/e2e/blog_actions.py
- read_file: src/forgel/daemon.py
- list_files
- read_file: src/forgel/approvals.py
- run: ['python', '-c', "import re,pathlib;t=pathlib.Path('src/forgel/cli.py').read_text();print(len(t.splitlines()));print(chr(10).join(f'{i+1}:{l}' for i,l in enumerate(t.splitlines()) if 'approv' in l.lower() or 'staging' in l.lower()))"]
- read_file: tests/e2e/README.md
- read_file: src/forgel/coding_agent.py
- read_file: src/forgel/task_review.py
- list_files
- read_file: src/forgel/task_qa.py
- run: ['ls', 'tests/e2e']
- run: ['python', '-m', 'unittest', 'tests.test_environment', '-v']
- read_file: src/forgel/templates/hello-web/environment.yaml
- read_file: src/forgel/config.py
- read_file: src/forgel/coding_agent.py

## Commands

- `['python', '-c', "import os; print('\\n'.join(sorted(os.listdir('tests'))))"]` -> exit 0
- `['python', '-c', "import os; print(chr(10).join(sorted(os.listdir('tests/e2e'))))"]` -> exit 0
- `['python', '-c', "import os; print(chr(10).join(sorted(os.listdir('tests'))))"]` -> exit 0
- `['python', '-m', 'unittest', 'tests.test_environment', '-v']` -> exit 0

## Recent Observations

- You have repeated this action several times. Its result is already above. Do not repeat it; make the edit or call done.
- src/forgel/coding_agent.py: lines 400-819 of 1291
0400|             str(task["id"]),
0401|             status="done" if status == "done" else "failed",
0402|             finished_at=_now(),
0403|             result={
0404|                 **previous_result,
0405|                 "summary": summary,
0406|                 "files_changed": attributed_files,
0407|                 "commands": commands,
0408|                 "test_output": _cap(test_output, 6000),
0409|                 "assumptions": assumptions,
0410|                 "context": context_stats,
0411|                 "test_removals": list(merged_removals.values()),
0412|                 "git": {
0413|                     "base": base_sha,
0414|                     "head": git_ops.head_sha(repo),
0415|                     "commit": commit_sha,
0416|                     "commits": attributed_commits,
0417|                 },
0418|                 "failure": (
0419|                     {"kind": failure_kind, "message": summary}
0420|                     if status == "failed"
0421|                     else {}
0422|                 ),
0423|                 "report": _ref(layout, report),
0424|             },
0425|         )
0426|         try:
0427|             if (layout.control / ".git").exists():
0428|                 if layout.is_linked:
0429|                     task_path = tasks.task_path(
0430|                         layout, str(task["id"])
0431|                     )
0432|                     refs = [_ref(layout, report)]
0433|                     try:
0434|                         refs.append(
0435|                             str(task_path.relative_to(layout.root))
0436|                         )
0437|                     except ValueError:
0438|                         pass
0439|                     git_ops.commit_paths(
0440|                         layout.root,
0441|                         refs,
0442|                         f"Agent report: {task['title']}",
0443|                     )
0444|                 else:
0445|                     git_ops.commit_all(
0446|                         layout.control, f"Agent report: {task['title']}"
0447|                     )
0448|                     git_ops.tag_baseline(layout.control)
0449|         except git_ops.GitOperationError:
0450|             pass
0451|         self._record_event(
0452|             layout,
0453|             project,
0454|             task,
0455|             status,
0456|             report,
0457|             summary,
0458|             files_changed,
0459|         )
0460|         if status == "failed":
0461|             log(
0462|                 f"[agent] {project['id']}: task {task['id']}: failed — "
0463|                 f"{summary[:200]}"
0464|             )
0465|         else:
0466|             log(f"[agent] {project['id']}: task {task['id']}: {status}")
0467|         return AgentResult(
0468|             status=status,
0469|             summary=summary,
0470|             steps=steps,
0471|             files_changed=files_changed,
0472|             commands=commands,
0473|             test_output=test_output,
0474|             report=_ref(layout, report),
0475|         )
0476| 
0477|     # ------------------------------------------------------------- sandbox
0478| 
0479|     def _open_runner(
0480|         self,
0481|         stack: ExitStack,
0482|         layout: ProjectLayout,
0483|         project: Mapping[str, Any],
0484|         repo_id: str,
0485|         environment: Environment | None,
0486|     ) -> CommandRunner | None:
0487|         """Enter the project sandbox when configured, or return ``None``.
0488| 
0489|         The repository is bind-mounted into the container, so file actions stay
0490|         on the host and only command execution moves into the sandbox.
0491|         """
0492| 
0493|         sandbox = docker_runner(self.settings)
0494|         if sandbox is None:
0495|             return None
0496|         if environment is None and not self.settings.sandbox_image:
0497|             raise AgentError(
0498|                 "FORGEL_SANDBOX=docker requires environment.yaml or "
0499|                 "FORGEL_SANDBOX_IMAGE"
0500|             )
0501|         available, detail = sandbox.available()
0502|         if not available:
0503|             raise AgentError(f"sandbox unavailable: {detail}")
0504|         try:
0505|             return stack.enter_context(
0506|                 sandbox.session(
0507|                     layout,
0508|                     environment,
0509|                     str(project["id"]),
0510|                     repo_id,
0511|                 )
0512|             )
0513|         except SandboxError as exc:
0514|             raise AgentError(f"sandbox: {exc}") from exc
0515| 
0516|     def _converse(
0517|         self,
0518|         layout: ProjectLayout,
0519|         repo: Path,
0520|         repo_id: str,
0521|         task: Mapping[str, Any],
0522|         model: str,
0523|         runner: CommandRunner | None,
0524|         environment: Environment | None,
0525|     ) -> tuple[
0526|         str,
0527|         str,
0528|         int,
0529|         list[str],
0530|         list[dict[str, Any]],
0531|         set[str],
0532|         str,
0533|         list[str],
0534|         dict[str, Any],
0535|         list[dict[str, str]],
0536|     ]:
0537|         """Run the model loop and the final test, returning the run state.
0538| 
0539|         The loop is session-based: when the estimated prompt size approaches
0540|         the context budget, or a session hits its step cap, the run writes a
0541|         durable state file and starts a new session from it. The model never
0542|         manages token counts or asks a human to continue.
0543|         """
0544| 
0545|         window = self._context_window(layout)
0546|         budget: ContextBudget = budget_for(window)
0547|         state_path = layout.artifact(
0548|             f"docs/program/agent/{task['id']}.state.md"
0549|         )
0550|         state_ref = _ref(layout, state_path) if state_path.exists() else ""
0551|         task_prompt = self._task_prompt(layout, task, repo_id, repo)
0552|         if state_path.exists():
0553|             previous = state_path.read_text(encoding="utf-8")
0554|             task_prompt += (
0555|                 "\n\n## Previous session state\n\n" + previous
0556|             )
0557|         messages: list[ModelMessage] = [
0558|             ModelMessage("system", SYSTEM_PROMPT),
0559|             ModelMessage("user", task_prompt),
0560|         ]
0561|         actions: list[str] = []
0562|         commands: list[dict[str, Any]] = []
0563|         touched: set[str] = set()
0564|         recent: list[str] = []
0565|         assumptions = [
0566|             str(item).strip()
0567|             for item in task.get("assumptions", [])
0568|             if str(item).strip()
0569|         ]
0570|         test_removals: list[dict[str, str]] = []
0571|         status = "failed"
0572|         summary = "step limit reached"
0573|         failure_kind = "agent"
0574|         invalid = 0
0575|         markup_retries = 0
0576|         steps = 0
0577|         sessions = 0
0578|         compactions = 0
0579|         signatures: dict[str, int] = {}
0580| 
0581|         def handoff(session: int) -> tuple[list[ModelMessage], str]:
0582|             changed = sorted(
0583|                 set(touched) | set(git_ops.status_paths(repo))
0584|             )
0585|             state = SessionState(
0586|                 task_id=str(task["id"]),
0587|                 title=str(task["title"]),
0588|                 session=session,
0589|                 requirements=[
0590|                     str(item) for item in task.get("requirements", [])
0591|                 ],
0592|                 acceptance=[
0593|                     str(item) for item in task.get("acceptance", [])
0594|                 ],
0595|                 constraints=[
0596|                     str(item) for item in task.get("constraints", [])
0597|                 ],
0598|                 assumptions=list(assumptions),
0599|                 files_changed=changed,
0600|                 actions=list(actions),
0601|                 commands=list(commands),
0602|                 observations=list(recent),
0603|             )
0604|             write_text(state_path, state.to_markdown())
0605|             return (
0606|                 [
0607|                     ModelMessage("system", SYSTEM_PROMPT),
0608|                     ModelMessage("user", self._task_prompt(
0609|                         layout, task, repo_id, repo
0610|                     ) + "\n\n" + handoff_prompt(state)),
0611|                 ],
0612|                 _ref(layout, state_path),
0613|             )
0614| 
0615|         terminal = False
0616|         for session in range(1, self.max_sessions + 1):
0617|             sessions = session
0618|             handed_off = False
0619|             for _step in range(1, self.max_steps + 1):
0620|                 steps += 1
0621|                 try:
0622|                     raw = self.client.complete(messages, model=model)
0623|                 except ModelError as exc:
0624|                     status = "failed"
0625|                     summary = f"model call failed: {exc}"
0626|                     failure_kind = "infrastructure"
0627|                     terminal = True
0628|                     break
0629|                 action = parse_action(raw)
0630|                 if action is None:
0631|                     if (
0632|                         _looks_like_tool_markup(raw)
0633|                         and markup_retries < 2
0634|                     ):
0635|                         messages.append(
0636|                             ModelMessage("assistant", raw)
0637|                         )
0638|                         messages.append(
0639|                             ModelMessage(
0640|                                 "user",
0641|                                 "Return exactly one JSON action object. "
0642|                                 "Do not use tool-call markup, XML or "
0643|                                 "provider-specific function calls.",
0644|                             )
0645|                         )
0646|                         markup_retries += 1
0647|                         continue
0648|                     invalid += 1
0649|                     messages.append(ModelMessage("assistant", raw))
0650|                     messages.append(
0651|                         ModelMessage(
0652|                             "user",
0653|                             "Invalid reply. Return exactly one JSON action "
0654|                             "object using one of: list_files, read_file, "
0655|                             "write_file, delete_file, run, done, fail. "
0656|                             "Do not return prose, a plan, tool-call markup "
0657|                             "or any other shape.",
0658|                         )
0659|                     )
0660|                     if invalid >= MAX_INVALID_REPLIES:
0661|                         status = "failed"
0662|                         summary = (
0663|                             "the model did not return a valid action "
0664|                             f"after {invalid} attempts"
0665|                         )
0666|                         terminal = True
0667|                         break
0668|                     continue
0669|                 invalid = 0
0670|                 markup_retries = 0
0671|                 kind = str(action["action"])
0672|                 messages.append(
0673|                     ModelMessage(
0674|                         "assistant",
0675|                         json.dumps(action, ensure_ascii=False),
0676|                     )
0677|                 )
0678|                 if kind == "done":
0679|                     status = "done"
0680|                     summary = str(action.get("summary", "")).strip() or (
0681|                         "agent reported done"
0682|                     )
0683|                     for item in action.get("assumptions", []):
0684|                         value = str(item).strip()
0685|                         if value and value not in assumptions:
0686|                             assumptions.append(value)
0687|                     for item in action.get("test_removals", []):
0688|                         if not isinstance(item, dict):
0689|                             continue
0690|                         test = str(item.get("test", "")).strip()
0691|                         reason = str(item.get("reason", "")).strip().lower()
0692|                         replacement = str(
0693|                             item.get("replacement", "")
0694|                         ).strip()
0695|                         if (
0696|                             test
0697|                             and reason in {"removed", "replaced", "wrong"}
0698|                         ):
0699|                             test_removals.append(
0700|                                 {
0701|                                     "test": test,
0702|                                     "reason": reason,
0703|                                     "replacement": replacement,
0704|                                 }
0705|                             )
0706|                     terminal = True
0707|                     break
0708|                 if kind == "fail":
0709|                     status = "failed"
0710|                     summary = str(action.get("reason", "")).strip() or (
0711|                         "agent reported failure"
0712|                     )
0713|                     terminal = True
0714|                     break
0715|                 signature = self._signature(action)
0716|                 repeats = 0
0717|                 if kind in {"read_file", "write_file", "run"}:
0718|                     repeats = signatures.get(signature, 0) + 1
0719|                     signatures[signature] = repeats
0720|                     if repeats >= MAX_REPEATED_ACTIONS:
0721|                         status = "failed"
0722|                         failure_kind = "agent"
0723|                         summary = (
0724|                             f"repeated action loop: {signature}"
0725|                         )
0726|                         terminal = True
0727|                         break
0728|                 observation, command = self._execute(
0729|                     layout,
0730|                     repo,
0731|                     action,
0732|                     touched,
0733|                     runner,
0734|                     environment.env_map if environment else None,
0735|                 )
0736|                 actions.append(self._action_summary(action))
0737|                 if command is not None:
0738|                     commands.append(command)
0739|                 recent.append(_cap(observation, MAX_OBSERVATION_CHARS))
0740|                 recent = recent[-6:]
0741|                 messages.append(
0742|                     ModelMessage(
0743|                         "user", f"OBSERVATION:\n{_cap(observation)}"
0744|                     )
0745|                 )
0746|                 if repeats >= 3:
0747|                     warning = (
0748|                         "You have repeated this action several times. Its "
0749|                         "result is already above. Do not repeat it; make the "
0750|                         "edit or call done."
0751|                     )
0752|                     messages.append(ModelMessage("user", warning))
0753|                     recent.append(warning)
0754|                 if kind in {"write_file", "delete_file"} and (
0755|                     observation.startswith(("wrote ", "deleted "))
0756|                 ):
0757|                     signatures.clear()
0758|                 if (
0759|                     budget.should_compact(messages, model)
0760|                     and session < self.max_sessions
0761|                 ):
0762|                     used = budget.usage(messages, model)
0763|                     messages, state_ref = handoff(session)
0764|                     invalid = 0
0765|                     compactions += 1
0766|                     handed_off = True
0767|                     print(
0768|                         f"[agent] {task['id']}: context handoff to "
0769|                         f"session {session + 1} "
0770|                         f"(~{used}/{budget.usable} tokens)"
0771|                     )
0772|                     break
0773|             if terminal:
0774|                 break
0775|             if not handed_off:
0776|                 if session < self.max_sessions:
0777|                     messages, state_ref = handoff(session)
0778|                     invalid = 0
0779|                     compactions += 1
0780|                     print(
0781|                         f"[agent] {task['id']}: step cap, handoff to "
0782|                         f"session {session + 1}"
0783|                     )
0784|                     continue
0785|                 status = "failed"
0786|                 summary = (
0787|                     f"step limit reached ({self.max_steps} per session x "
0788|                     f"{sessions} sessions)"
0789|                 )
0790|                 break
0791| 
0792|         test_output = ""
0793|         if status == "done":
0794|             test_command = [
0795|                 str(item) for item in task.get("test_command", [])
0796|             ]
0797|             if test_command:
0798|                 code, output = self._run_command(
0799|                     layout,
0800|                     repo,
0801|                     test_command,
0802|                     timeout=120,
0803|                     runner=runner,
0804|                     extra_env=environment.env_map if environment else None,
0805|                 )
0806|                 test_output = output
0807|                 commands.append(
0808|                     {
0809|                         "command": test_command,
0810|                         "exit_code": code,
0811|                         "final_test": True,
0812|                     }
0813|                 )
0814|                 if code != 0:
0815|                     status = "failed"
0816|                     failure_kind = "qa"
0817|                     summary += f"; final test command exited {code}"
0818|         context_stats = {
0819|             "window": window,
... use read_file with offset=820 to continue
- You have repeated this action several times. Its result is already above. Do not repeat it; make the edit or call done.

## Next Step

Continue the task from the requirements and the current repository state.
