# GENERALIST INTELLIGENCE ARCHITECTURE

## Purpose

This layer exists only to solve a concrete AXXEL problem:

> AXXEL must use a replaceable generalist model as its default cognitive engine,
> while preserving project memory, state, tools, policies, recipes, and governance outside the model.

It is NOT a collection of AI research ideas.
It is an operational layer that answers:
- which model should execute this task?
- what context does it need?
- what capabilities can be reused?
- when is specialization justified?
- how do we compare a new generalist against an existing specialist?
- how do we avoid retraining or rebuilding for every task?

---

## Where it fits

```text
CONTROL TOWER
    ↓
TASK CONTRACT
    ↓
CONTEXT COMPILER
    ↓
GENERALIST INTELLIGENCE LAYER
    ↓
CAPABILITY COMPOSER
    ↓
TOOLS / AGENT RUNTIME
    ↓
EXECUTION
    ↓
EVALUATOR
```

This layer does not own:
- project state;
- long-term memory;
- risk policy;
- data certification;
- task queue;
- deployment lifecycle.

Those remain in their existing AXXEL components.

---

## Core components

### 1. Model Abstraction
A common interface so AXXEL is not tied to one provider/model.

### 2. Context Compiler
Builds the task packet from:
- objective;
- current task;
- current subtask;
- relevant memory;
- current state;
- tools;
- constraints;
- acceptance criteria.

### 3. Capability Registry
Lists reusable capabilities and their contracts.

### 4. Capability Composer
Combines existing capabilities before creating a new specialist.

### 5. Generalist-First Router
Default path:
`GENERALIST → TOOLS/CONTEXT → EVALUATE`

Only if the task fails repeatedly and materially:
`SPECIALIST_CANDIDATE`

### 6. Specialist Exception Gate
A specialist is allowed only when it demonstrates material, reproducible advantage.

### 7. Benchmark Harness
Compares:
- reliability;
- task success;
- throughput;
- latency;
- cost;
- intervention rate;
- safety/non-regression.

### 8. Specialist Retirement
When a newer generalist reaches required parity, the specialist is retired.

---

## Rules

1. **GENERALIST_FIRST**
2. **COMPOSE_BEFORE_SPECIALIZE**
3. **MEMORY_OUTSIDE_MODEL**
4. **SPECIALIST_REQUIRES_MEASURED_ADVANTAGE**
5. **REBENCHMARK_ON_MODEL_UPGRADE**
6. **RETIRE_SPECIALIST_WHEN_NO_LONGER_NEEDED**

---

## What is NOT required now

This layer is NOT a PHASE_1 priority.

Do not delay:
`DATA_INTEGRITY_AND_CERTIFICATION`

to build:
- model routing;
- specialist retirement;
- generalist benchmarks;
- compositional benchmark suites.

These remain future work until the foundation and Control Tower exist.

---

## Minimum implementation order

### GI-001 — Model abstraction interface
Depends on: Control Tower + Agent Runtime contract

### GI-002 — Context Compiler
Depends on: state + task contract + memory interfaces

### GI-003 — Capability Registry
Depends on: stable tool/capability contracts

### GI-004 — Capability Composer
Depends on: Capability Registry

### GI-005 — Generalist-first router
Depends on: benchmark harness

### GI-006 — Benchmark harness
Depends on: Evaluator + Observability

### GI-007 — Specialist exception gate
Depends on: benchmark harness

### GI-008 — Specialist retirement workflow
Depends on: specialist registry + rollback

---

## Exit criteria

This layer is considered functional when:

1. A task can be passed to a generalist through a stable interface.
2. Context is assembled from AXXEL state instead of hard-coded prompts.
3. Existing capabilities can be composed.
4. A specialist cannot be introduced without benchmark evidence.
5. Model upgrades do not erase memory/state.
6. A specialist can be removed safely when the generalist reaches parity.

---

## Cross-context compositional generalization

AXXEL must not evaluate the generalist only on tasks seen in familiar combinations.

It should also test whether already-known capabilities transfer to new contexts without
task-specific retraining.

Examples for AXXEL:

```text
KNOWN:
- validate data
- XAUUSD
- M1

NEW COMBINATION:
- validate data
- US500Cash
- M5
```

or:

```text
KNOWN:
- research anomaly
- time-window analysis

KNOWN:
- transaction-cost evaluator

NEW COMBINATION:
- research a new temporal anomaly
- on a different asset
- with a different cost regime
- using the same reusable capabilities
```

The goal is to distinguish:

```text
MEMORIZATION OF KNOWN WORKFLOWS
from
TRANSFER OF REUSABLE CAPABILITIES
```

### Required benchmark dimensions

The Generalist Benchmark Harness should include:

- known task / known context;
- known task / new context;
- new composition of known capabilities;
- new asset or data source;
- new tool implementation behind the same interface;
- new ordering of known subtasks.

### Cross-Context Transfer Rate

```text
successful_tasks_in_unseen_contexts
/
attempted_tasks_in_unseen_contexts
```

### Composition Transfer Rate

```text
successful_novel_combinations_of_known_capabilities
/
attempted_novel_combinations
```

A high score indicates that AXXEL is learning reusable concepts and capability contracts
rather than merely reproducing hard-coded workflows.

