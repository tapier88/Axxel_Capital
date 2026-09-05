# MASTER ROADMAP

## P0 — FOUNDATION — AHORA

### Objetivo
Cerrar `DATA_INTEGRITY_AND_CERTIFICATION`.

### Entregables
- Data Engine V1 completo.
- Dataset registry.
- Data manifests.
- Integrity tests.
- Timezone/session certification.
- Missing/duplicate/out-of-order checks.
- Provenance.
- Reproducible data snapshots.
- Cost-source labels.
- Evidence artifact.

### Exit Gate
`DATA_ENGINE_CERTIFIED = TRUE`

Actualización 2026-09-04: ADR-FOUNDATION-001 aprobado; implementación mínima
FOUNDATION_SCOPE_READINESS_V1 terminada en SHADOW con fixtures. G1 probado; G5/G6
demostrados únicamente en la frontera SHADOW. G3 (ruta histórica verificable) y G4
(captura XM forward cualificada) siguen pendientes. La preparación operacional por
alcance no sustituye el booleano de certificación. Foundation permanece BLOCKED,
DATA_ENGINE_CERTIFIED=false y Control Tower bloqueado. Evidencia y siguientes
autorizaciones: `reports/foundation_scope_shadow/2026-09-04/FOUNDATION_REPORT.md`.

---

# P1 — CONTROL TOWER

### Construir
- state machine;
- task queue;
- dependency graph;
- priority selector;
- task contracts;
- permissions;
- run manifests.

### Exit Gate
AXXEL puede determinar:
- qué hacer;
- por qué;
- qué lo bloquea;
- cuándo parar.

---

# P2 — OBSERVABILITY

### Construir
- structured telemetry;
- trace IDs;
- metrics store;
- failure logging;
- cost/time accounting;
- run history;
- mission-control backend.

### Exit Gate
Toda decisión importante es auditable.

---

# P3 — EXPERIENCE

### Construir
- experience schema;
- success/failure/intervention/discovery store;
- intervention capture;
- evidence linking.

### Exit Gate
Cada tarea genera experiencia estructurada.

---

# P4 — LEARNING

### Construir
- lesson extraction;
- recurring-failure detection;
- policy memory;
- recipe memory;
- confidence/versioning.

### Exit Gate
AXXEL puede demostrar que una lección reduce un fallo repetido.

---

# P5 — IMPROVEMENT

### Construir
- bottleneck detector;
- process auditor;
- improvement hypothesis generator;
- priority scoring;
- champion/challenger.

### Exit Gate
Al menos una mejora de proceso validada end-to-end.

---

# P6 — ARCHITECTURE EVOLUTION

### Construir
- architecture gap detector;
- capability graph;
- missing capability registry;
- architecture proposals;
- change gates;
- promotion/rollback.

### Exit Gate
Un gap real detectado → challenger → validación → promoción controlada.

---

# P7 — AUTONOMY

### Construir
- autonomy metrics;
- intervention rate;
- escalation policy;
- safe bounded autonomy;
- confidence thresholds.

### Exit Gate
Reducción demostrable de intervención humana sin pérdida de confiabilidad.

---

# P8 — WATCHDOGS + RECOVERY

### Construir
- process watchdog;
- stale-task detector;
- crash recovery;
- data feed degradation;
- broker/API degradation;
- state reconciliation;
- safe shutdown.

### Exit Gate
El sistema se recupera de fallos simulados sin corrupción.

---

# P9 — PAPER/DEMO EXECUTION

### Construir
- live data;
- signal lifecycle;
- execution adapter;
- demo account;
- slippage/spread capture;
- risk engine;
- reconciliation;
- post-trade evaluator.

### Exit Gate
Consistent demo evidence.

---

# P10 — PRODUCTION CANDIDATE

No es una promesa de live.

Requiere:
- estabilidad;
- risk approval;
- audit;
- demo evidence;
- rollback;
- explicit human approval.


---

# P11 — GENERALIST INTELLIGENCE

**Prerequisites:** Control Tower, Observability, Evaluator, Experience Engine.

Build:
- model abstraction;
- context compiler;
- capability registry/composer;
- generalist-first router;
- specialist exception/retirement.

Do not start before prerequisites.

---

# P12 — HIERARCHICAL AGENT CONTROL

**Prerequisite:** stable task contracts and state machine.

Build:
- task/subtask hierarchy;
- next-subtask planning;
- bounded context packets;
- completion tests;
- repair/replan loop.

---

# P13 — SHARED FOUNDATION REUSE

Integrate into existing Data + Experience layers:
- certified asset reuse;
- provenance/trust tiers;
- reuse-before-acquire;
- failed trajectory retention;
- project delta acquisition.

This is an integration milestone, not a new top-level autonomous engine.
