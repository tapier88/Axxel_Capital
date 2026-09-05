# AGENT CONTROL LOOP

## Purpose

This layer solves one operational problem:

> Large AXXEL tasks must be decomposed into measurable subtasks,
> and the agent must receive only the context required to execute the current subtask.

It is part of the Control Tower / Orchestrator path, not an independent research subsystem.

---

## Control flow

```text
GOAL
  ↓
CONTROL TOWER
  ↓
PLANNER
  ↓
NEXT SUBTASK
  ↓
CONTEXT COMPILER
  ↓
AGENT RUNTIME
  ↓
EXECUTION
  ↓
EVALUATOR
  ↓
DONE / REPAIR / REPLAN
```

---

## Task hierarchy

```text
MISSION
→ PHASE
→ EPIC
→ TASK
→ SUBTASK
→ ACTION
```

Only the current level and necessary parent context should be sent to the agent.

---

## Context Packet

```yaml
task_id:
subtask_id:
objective:
current_state:
relevant_memory:
available_tools:
constraints:
acceptance_criteria:
expected_output:
stop_conditions:
```

Optional metadata may include:
- provenance;
- confidence;
- episode quality;
- recent trace;
- target state.

Do not include metadata unless it changes execution quality or auditability.

---

## Planner responsibilities

The planner chooses:
- next subtask;
- dependencies;
- completion test;
- whether to repair or replan.

The agent chooses:
- local implementation actions inside the assigned subtask.

---

## Replanning triggers

Replan when:
- acceptance test fails;
- dependency changes;
- evidence invalidates assumptions;
- task becomes blocked;
- resource budget exceeded;
- architecture gap detected;
- human intervention changes direction.

---

## Exit criteria

Functional when AXXEL can:
1. decompose a task;
2. assign one bounded subtask;
3. compile relevant context;
4. execute and test it;
5. update state;
6. choose the next subtask or stop.


---

## Instruction ablation

The usefulness of task/subtask instructions must be measurable.

AXXEL should periodically compare:

```text
WITH TASK/SUBTASK INSTRUCTION
vs
WITHOUT TASK/SUBTASK INSTRUCTION
```

on representative tasks.

If instructions materially improve:
- success rate;
- next-action quality;
- reliability;
- intervention rate;

then they remain mandatory fields in the Context Packet.

This turns "more context is better" into an empirical rule instead of an assumption.

### Required metric

```text
INSTRUCTION_LIFT =
performance_with_instruction
-
performance_without_instruction
```

If lift is negligible, simplify the context.
If lift is material, preserve the field.

---

## Metadata as disambiguation context

Metadata is especially valuable when two trajectories look similar at the action level
but differ in quality, source, task intent, or outcome.

The Context Compiler should include metadata only when it helps the agent interpret:
- why an action was taken;
- whether the example is trustworthy;
- what task/subtask it belonged to;
- whether the result was successful;
- whether a human had to intervene.

The objective is not to maximize context size.

The objective is to make heterogeneous experience interpretable.

