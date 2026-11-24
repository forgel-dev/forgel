"""Shared prompt fragments for roles that act on tasks.

The task-reference rule has one source so every instruction that lets a model
choose a task resolves it the same way.
"""

TASK_REFERENCE_RULES = """
Task references:
- A task may be named by its id or file name, its title, or its description.
  Pass that reference as task_id; the runtime resolves it. An ambiguous
  reference is rejected with the candidates, so do not guess.
- Omit task_id only for the current or last task. The runtime then picks a
  running task first, otherwise the task launched most recently.
"""
