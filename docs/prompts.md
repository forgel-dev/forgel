# Prompt Discipline

A prompt carries only **role, state, task, constraints and the provenance of
its context**. Nothing else. This is a project rule, not a style preference.

## Non-Negotiables

1. **No concrete scenarios.** A prompt never contains a failure example, an
   incident, a bug, a named provider, tool, credential, environment or a
   sequence of steps.
2. **No prompt patches.** Never encode a fix for one observed case as prompt
   prose. Fix the context construction, the role boundary or the runtime.
3. **Capabilities are structured state.** An agent receives its own
   capabilities as data. It does not infer them from another agent's report,
   from an artifact, or from earlier conversation.
4. **Context is scoped by producer.** A run, report or artifact describes the
   agent and environment that produced it, not the current agent.
5. **History has producers.** The conversation stores the user's dialogue,
   this agent's own turns and the user-visible reports, each labeled by
   producer. A report is never relabeled as this agent's own state.
6. **A rule must stand without an example.** If it cannot be stated without
   one, it is not a rule yet: design the data and the boundary.
7. **Review rejects scenario prose.** A prompt change that adds a scenario,
   incident, named provider/tool/credential/environment or step-by-step
   script does not pass review.

## Context Model

Different roles are different agents. They may run in different processes,
sandboxes, homes, network namespaces and permission sets. The only safe model
is:

- every agent gets **its own** capabilities and its own artifacts;
- every context block names its producer and the run it belongs to;
- shared conversation is the user's dialogue plus this agent's own turns plus
  user-visible reports, each with its producer;
- a failure or a permission of one run is evidence about that run only.

When an agent needs to know what it can do, the runtime passes that as
structured state. It is not written in prose and it is not recovered from
history.

## What To Do Instead

- Change the context builder so the right structured state reaches the agent.
- Change the role boundary so one agent's environment does not leak into
  another's context.
- Change the runtime capability provider so an agent learns its own
  capabilities.
- Pass structured evidence — status, fields, references — and let the model
  reason from it.

## Applying the Rule

This applies to every prompt: project agent, planner, spec writer, coder,
reviewer, QA, release audit, outcome explainer and conversation compaction.
It also applies to generated project instruction files.

The canonical summaries are in [AGENTS.md](../AGENTS.md) **Prompt Rules** and
[FORGEL.md](../FORGEL.md) **Prompts**.
