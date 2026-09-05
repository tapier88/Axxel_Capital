# DETAILED TASK BACKLOG

## Prioridad vigente - publicacion baseline

Data Engine IMPLEMENTED; SHADOW implementado. AHORA G3 NOT_ESTABLISHED y G4 false.
V1 revocada; V2 IMPLEMENTED_AWAITING_START_APPROVAL, activation=false, T0=null.
DATA_ENGINE_CERTIFIED=false; Control Tower BLOCKED. Publicacion GitHub: COMPLETADA; no avance de fase.
Despues, revisar blockers G3/G4 bajo autorizacion separada. Los epics siguientes son
desglose del roadmap; no todos estan implementados ni autorizados.


Esta es la lista inicial de tareas. El agente debe convertir cada una en tickets pequeños y verificables.

---

# EPIC 0 — Preserve Existing System

### SAFE-001 — Snapshot baseline
- guardar commit/hash;
- listar carpetas;
- listar tests;
- listar config;
- crear baseline manifest.
**Acceptance:** baseline reproducible.

### SAFE-002 — Protected-path registry
- declarar paths protegidos;
- documentar restricciones.
**Acceptance:** agente puede verificar antes de escribir.

### SAFE-003 — Rollback procedure
- definir restore por cambio.
**Acceptance:** simulación de rollback pasa.

---

# EPIC 1 — Data Engine Certification

### DATA-001 — Data source inventory
### DATA-002 — Dataset provenance schema
### DATA-003 — Timestamp integrity
### DATA-004 — Duplicate detection
### DATA-005 — Ordering validation
### DATA-006 — OHLC validity
### DATA-007 — NaN/Inf validation
### DATA-008 — Spread validity
### DATA-009 — Timezone normalization
### DATA-010 — Session map certification
### DATA-011 — Symbol metadata certification
### DATA-012 — Sampling consistency M1/M5/M15/H1/D1
### DATA-013 — Data gap report
### DATA-014 — Train/DEV/VAL/OOS boundary protection
### DATA-015 — Dataset hashing/versioning
### DATA-016 — Reproducible snapshot builder
### DATA-017 — Cost-source tagging
### DATA-018 — Confidence per cost source
### DATA-019 — Full certification report
### DATA-020 — Data Engine exit gate

**Exit:** `DATA_ENGINE_CERTIFIED=true`.

---

# EPIC 2 — Control Tower

### CTRL-001 — Define global state schema
### CTRL-002 — Define task schema
### CTRL-003 — Implement task queue
### CTRL-004 — Implement dependency graph
### CTRL-005 — Implement task status transitions
### CTRL-006 — Implement priority scoring
### CTRL-007 — Implement bottleneck field
### CTRL-008 — Implement stop conditions
### CTRL-009 — Implement allowed/protected paths
### CTRL-010 — Implement agent assignment
### CTRL-011 — Implement run manifest
### CTRL-012 — State reconciliation test

---

# EPIC 3 — Observability

### OBS-001 — Trace ID standard
### OBS-002 — Structured event schema
### OBS-003 — Task start/end logging
### OBS-004 — Tool-call logging
### OBS-005 — Error taxonomy
### OBS-006 — Metric registry
### OBS-007 — Cost accounting
### OBS-008 — Duration accounting
### OBS-009 — Test-result capture
### OBS-010 — Artifact linkage
### OBS-011 — Failure cluster table
### OBS-012 — Mission Control API
### OBS-013 — Mission Control UI

---

# EPIC 4 — Experience Engine

### EXP-001 — Experience schema
### EXP-002 — Success store
### EXP-003 — Failure store
### EXP-004 — Intervention store
### EXP-005 — Discovery store
### EXP-006 — Evidence references
### EXP-007 — Experience confidence
### EXP-008 — Similar-experience retrieval
### EXP-009 — De-duplication
### EXP-010 — Experience audit

---

# EPIC 5 — Learning Engine

### LEARN-001 — Lesson schema
### LEARN-002 — Failure recurrence detector
### LEARN-003 — Intervention lesson extractor
### LEARN-004 — Success-pattern extractor
### LEARN-005 — Contradiction detector
### LEARN-006 — Confidence updater
### LEARN-007 — Policy memory
### LEARN-008 — Recipe memory
### LEARN-009 — Versioning
### LEARN-010 — Lesson effectiveness test

---

# EPIC 6 — Improvement Engine

### IMP-001 — Bottleneck detector
### IMP-002 — Process auditor
### IMP-003 — Improvement hypothesis schema
### IMP-004 — Impact estimator
### IMP-005 — Effort estimator
### IMP-006 — Risk estimator
### IMP-007 — Priority function
### IMP-008 — Challenger builder
### IMP-009 — Experiment isolation
### IMP-010 — Champion/challenger comparator
### IMP-011 — Promotion gate
### IMP-012 — Rollback trigger

---

# EPIC 7 — Architecture Gap Detector

### GAP-001 — Gap schema
### GAP-002 — Failure-to-gap classifier
### GAP-003 — Missing-data detection
### GAP-004 — Missing-tool detection
### GAP-005 — Missing-process detection
### GAP-006 — Missing-observability detection
### GAP-007 — Missing-recovery detection
### GAP-008 — Missing-risk-capability detection
### GAP-009 — Capability graph
### GAP-010 — Gap prioritization
### GAP-011 — Architecture proposal generator
### GAP-012 — Architecture validation gate

---

# EPIC 8 — Autonomy

### AUTO-001 — Eligible-task definition
### AUTO-002 — Autonomy metric
### AUTO-003 — Intervention-rate metric
### AUTO-004 — Escalation policy
### AUTO-005 — Confidence thresholds
### AUTO-006 — Low-risk auto-execution
### AUTO-007 — Human approval queue
### AUTO-008 — Intervention feedback loop
### AUTO-009 — Autonomy regression detector
### AUTO-010 — Reliability-preserving autonomy gate

---

# EPIC 9 — Watchdogs and Recovery

### WDG-001 — Process watchdog
### WDG-002 — Task timeout
### WDG-003 — Stale state detector
### WDG-004 — Crash restart
### WDG-005 — Data feed watchdog
### WDG-006 — Broker/API watchdog
### WDG-007 — Disk/storage watchdog
### WDG-008 — State corruption detector
### WDG-009 — Safe shutdown
### WDG-010 — Recovery drill

---

# EPIC 10 — Research Engine Hardening

### RES-001 — Hypothesis preregistration enforcement
### RES-002 — Multiple-testing/FDR enforcement
### RES-003 — Walk-forward standard
### RES-004 — Purging/embargo standard
### RES-005 — OOS lock
### RES-006 — Skeptic agent
### RES-007 — Robustness battery
### RES-008 — Regime consistency
### RES-009 — Monte Carlo
### RES-010 — Economic significance
### RES-011 — Research value score
### RES-012 — Rejection reason taxonomy

---

# EPIC 11 — Cost Reality

### COST-001 — Source hierarchy
### COST-002 — REAL_TICK_COST schema
### COST-003 — PROXY_COST schema
### COST-004 — Confidence model
### COST-005 — Spread/slippage decomposition
### COST-006 — Broker/source metadata
### COST-007 — Cost uncertainty bands
### COST-008 — Economic viability gate
### COST-009 — Historical tick acquisition plan
### COST-010 — Cost reality report

---

# EPIC 12 — Risk Capital

### RISK-001 — Capital state
### RISK-002 — Risk budget
### RISK-003 — Position sizing
### RISK-004 — Per-strategy limits
### RISK-005 — Portfolio exposure
### RISK-006 — Drawdown limits
### RISK-007 — Loss intelligence
### RISK-008 — Kill switch
### RISK-009 — Risk audit
### RISK-010 — Risk gate tests

---

# EPIC 13 — Strategy Portfolio

### PORT-001 — Strategy registry
### PORT-002 — Lifecycle state
### PORT-003 — Correlation matrix
### PORT-004 — Redundancy detector
### PORT-005 — Capital allocator
### PORT-006 — Regime activation
### PORT-007 — Strategy retirement
### PORT-008 — Portfolio stress

---

# EPIC 14 — Live/Paper Data

### LIVE-001 — Live data adapter
### LIVE-002 — Timestamp reconciliation
### LIVE-003 — Quote health
### LIVE-004 — Spread capture
### LIVE-005 — Tick persistence
### LIVE-006 — Latency measurement
### LIVE-007 — Broker session status
### LIVE-008 — Data fallback policy

---

# EPIC 15 — Demo Execution

### DEMO-001 — Execution interface
### DEMO-002 — MT5 adapter
### DEMO-003 — Order state machine
### DEMO-004 — Fill reconciliation
### DEMO-005 — Slippage capture
### DEMO-006 — Risk pre-check
### DEMO-007 — Emergency stop
### DEMO-008 — Post-trade evaluation
### DEMO-009 — Demo performance report
### DEMO-010 — Demo promotion gate

---

# EPIC 16 — Fundamental Intelligence

### FUND-001 — Define allowed sources
### FUND-002 — PIT macro requirements
### FUND-003 — Calendar ingestion
### FUND-004 — Event normalization
### FUND-005 — Surprise computation
### FUND-006 — Provenance
### FUND-007 — Leakage tests
### FUND-008 — Feature integration
### FUND-009 — Incremental-value test

---

# EPIC 17 — Drift + Continuous Learning

### DRIFT-001 — Data drift
### DRIFT-002 — Feature drift
### DRIFT-003 — Prediction drift
### DRIFT-004 — Performance drift
### DRIFT-005 — Cost drift
### DRIFT-006 — Regime drift
### DRIFT-007 — Alert thresholds
### DRIFT-008 — Retraining trigger proposal
### DRIFT-009 — Challenger retraining
### DRIFT-010 — Promotion test

---

# EPIC 18 — Mission Control

### UI-001 — Phase widget
### UI-002 — Bottleneck widget
### UI-003 — Current-task widget
### UI-004 — Reliability
### UI-005 — Autonomy
### UI-006 — Throughput
### UI-007 — Intervention rate
### UI-008 — Failures
### UI-009 — Architecture gaps
### UI-010 — Challengers
### UI-011 — Trading lifecycle
### UI-012 — Risk
### UI-013 — Costs
### UI-014 — Human approval inbox

---

# EPIC 19 — Self-Evolution

### META-001 — Recipe performance history
### META-002 — Improvement-method performance
### META-003 — Meta-bottleneck detection
### META-004 — Which improvement method works best?
### META-005 — Self-assessment report
### META-006 — Architecture evolution history
### META-007 — Improvement regression test
### META-008 — Long-term autonomy report

---

# ORDEN DE EJECUCIÓN INICIAL

1. `SAFE-001`
2. `SAFE-002`
3. `DATA-001 ... DATA-020`
4. `CTRL-001 ... CTRL-012`
5. `OBS-001 ... OBS-013`
6. `EXP-001 ... EXP-010`
7. `LEARN-001 ... LEARN-010`
8. `IMP-001 ... IMP-012`
9. `GAP-001 ... GAP-012`
10. continuar por dependencia y valor.

No ejecutar todos los epics en paralelo.

---

# EPIC 20 — Generalist Intelligence Layer

> FUTURE. BLOCKED until Control Tower, Observability, Evaluator and Experience Engine are functional.

### GI-001 — Model abstraction interface
### GI-002 — Context Compiler
### GI-003 — Capability Registry
### GI-004 — Capability Composer
### GI-005 — Generalist-first routing
### GI-006 — Generalist benchmark harness
### GI-007 — Specialist exception gate
### GI-008 — Specialist registry
### GI-009 — Generalist-vs-specialist comparator
### GI-010 — Specialist retirement workflow
### GI-011 — Model upgrade re-benchmark
### GI-012 — Generalist regression tests
### GI-013 — Cross-context transfer benchmark
### GI-014 — Novel composition benchmark
### GI-015 — New-asset/new-tool transfer tests
### GI-016 — Cross-Context Transfer Rate
### GI-017 — Composition Transfer Rate

**Exit Gate:** AXXEL uses one generalist interface by default, composes existing capabilities,
and only introduces or retains specialists when measurable evidence justifies them.

---

# EPIC 21 — Hierarchical Agent Control

> FUTURE. Depends on Control Tower, task contracts and stable state transitions.

### HAC-001 — Mission/phase/epic/task/subtask hierarchy
### HAC-002 — Subtask schema
### HAC-003 — Next-subtask planner
### HAC-004 — Context Packet
### HAC-005 — Relevant-memory retrieval
### HAC-006 — Subtask completion evaluator
### HAC-007 — Repair/replan rules
### HAC-008 — State update after subtask
### HAC-009 — Planning vs execution trace separation
### HAC-010 — Hierarchical control integration test
### HAC-011 — Instruction ablation benchmark
### HAC-012 — Instruction Lift metric
### HAC-013 — Context simplification rule
### HAC-014 — Context metadata relevance test
### HAC-015 — Metadata-conditioned noisy-data benchmark

**Exit Gate:** AXXEL can decompose a long task, execute one bounded subtask with the right
context, evaluate it, update state and select the next subtask or stop.

---

# EPIC 22 — Shared Foundation Reuse

> FUTURE INTEGRATION MILESTONE. Lives inside Data Engine + Experience Engine; it is not a separate autonomous engine.

### SFR-001 — Dataset registry and provenance
### SFR-002 — Gold/Silver/Bronze trust tiers
### SFR-003 — Reuse-before-acquire gate
### SFR-004 — Dataset lineage/versioning
### SFR-005 — Project data contract
### SFR-006 — Failed-trajectory retention
### SFR-007 — Experience quality/confidence metadata
### SFR-008 — Time-to-experiment metric
### SFR-009 — Duplicate asset detector
### SFR-010 — Shared-foundation integration test
### SFR-011 — Data Diversity Score
### SFR-012 — Task/regime/failure-mode coverage metrics
### SFR-013 — Dataset diversity ablation
### SFR-014 — Metadata completeness score
### SFR-015 — Low-quality experience admission gate

**Exit Gate:** New projects reuse certified data and prior experience instead of rebuilding
from zero, without contaminating certified datasets with lower-trust evidence.

