# AXXEL MASTER PLAN V2

## 1. Misión

Construir AXXEL CAPITAL como un sistema autónomo de investigación, decisión y ejecución cuantitativa capaz de:

- descubrir oportunidades;
- probarlas científicamente;
- rechazar rápidamente ideas débiles;
- acumular experiencia;
- aprender de errores e intervenciones;
- detectar capacidades faltantes;
- mejorar procesos;
- crear challengers;
- validar mejoras;
- operar con supervisión humana externa al flujo diario;
- evolucionar sin destruir capacidades validadas.

AXXEL no se considera terminado.

Su estado permanente es:

`CONTINUOUS_MEASURABLE_IMPROVEMENT`

---

# 2. Estado actual

```yaml
phase: PHASE_1_FOUNDATION
primary_bottleneck: G3_HISTORICAL_ROUTE_AND_G4_XM_FORWARD_QUALIFICATION
current_task: AXXEL_GITHUB_BASELINE_PUBLISHED
north_star: REPRODUCIBLE_RISK_ADJUSTED_NET_EDGE
human_role: HUMAN_ON_THE_LOOP
real_deployment: BLOCKED
```

Data Engine V1 ya esta implementado; faltan G3/G4 y certificacion. Esta tarea publica la baseline sin iniciar esos trabajos.

**No se cambia esta prioridad por introducir V2.**

V2 agrega la capa que permitirá que AXXEL aprenda y evolucione una vez que sus fundamentos estén certificados.

---

# 3. Dónde está el agente

El agente NO es toda la arquitectura.

El agente vive dentro de:

`AGENT_RUNTIME`

y recibe tareas del:

`CONTROL_TOWER / ORCHESTRATOR`

El agente:

- observa estado;
- ejecuta tareas autorizadas;
- genera artefactos;
- registra trazas;
- solicita herramientas;
- reporta resultados;
- propone mejoras.

El agente NO puede unilateralmente:

- alterar guardrails;
- reducir pruebas;
- eliminar gates;
- desplegar a real;
- promover modelos;
- modificar parámetros de riesgo críticos;
- borrar evidencia;
- reescribir historia;
- declarar una estrategia rentable sin validación.

---

# 4. Arquitectura objetivo

AXXEL V2 se organiza en ocho loops:

1. **Execution Loop**
2. **Evaluation Loop**
3. **Experience Loop**
4. **Learning Loop**
5. **Improvement Loop**
6. **Architecture Evolution Loop**
7. **Autonomy Loop**
8. **Governance Loop**

Flujo:

```text
GOALS
  ↓
CONTROL TOWER
  ↓
PLANNER
  ↓
ORCHESTRATOR
  ↓
AGENT RUNTIME
  ↓
EXECUTION
  ↓
RESULT + TRACE
  ↓
EVALUATOR
  ↓
SCORE / REWARD / DECISION
  ↓
EXPERIENCE STORE
  ↓
LESSON EXTRACTION
  ↓
POLICY / RECIPE UPDATE PROPOSAL
  ↓
IMPROVEMENT ENGINE
  ↓
PROCESS GAP or ARCHITECTURE GAP
  ↓
CHALLENGER
  ↓
SHADOW / SANDBOX
  ↓
VALIDATION
  ↓
PROMOTE or REJECT
  ↓
NEW VERSION
```

---

# 5. Resultado final deseado

AXXEL debe poder contestar en cualquier momento:

### Estado
- ¿Dónde estoy?
- ¿Qué está funcionando?
- ¿Qué está degradado?
- ¿Qué está bloqueado?

### Dirección
- ¿Cuál es el objetivo?
- ¿Cuál es el cuello de botella?
- ¿Cuál es el siguiente mejor paso?

### Aprendizaje
- ¿Qué aprendí?
- ¿Qué errores estoy repitiendo?
- ¿Qué intervenciones humanas recibí?
- ¿Qué políticas debo cambiar?

### Arquitectura
- ¿Qué capacidad me falta?
- ¿Cuál es la evidencia de que la necesito?
- ¿Qué mejora propondría?
- ¿Cómo la probaría sin romper el sistema?

### Negocio/trading
- ¿Qué genera valor?
- ¿Qué destruye valor?
- ¿Qué estrategia tiene edge reproducible neto de costes?
- ¿Qué riesgo consume?
- ¿Debe avanzar, esperar o morir?

---

# 6. Definición de éxito

AXXEL no se evalúa por cantidad de código.

Se evalúa por:

```text
AUTONOMY
RELIABILITY
VALIDATED THROUGHPUT
COST EFFICIENCY
FAILURE RECURRENCE
INTERVENTION RATE
LEARNING RATE
IMPROVEMENT VELOCITY
NET RISK-ADJUSTED VALUE
```

La métrica financiera final sigue siendo:

`REPRODUCIBLE_RISK_ADJUSTED_NET_EDGE`

---

# 7. Fases maestras

## PHASE 1 — FOUNDATION
Certificar datos, estado, reproducibilidad y gates.

## PHASE 2 — CONTROL
Construir Control Tower, task lifecycle, permisos y state machine.

## PHASE 3 — OBSERVABILITY
Trazas, métricas, costes, failure clustering y dashboard.

## PHASE 4 — EXPERIENCE
Registrar éxitos, fallos, intervenciones y discoveries estructurados.

## PHASE 5 — LEARNING
Extraer lecciones y proponer policy/recipe updates.

## PHASE 6 — IMPROVEMENT
Detectar cuellos de botella, probar mejoras y comparar champion/challenger.

## PHASE 7 — ARCHITECTURE EVOLUTION
Detectar gaps estructurales y crear capacidades faltantes bajo gates.

## PHASE 8 — AUTONOMY
Reducir intervención humana conservando o aumentando confiabilidad.

## PHASE 9 — PAPER/DEMO
Ejecución completa en demo con watchdogs y recuperación.

## PHASE 10 — PRODUCTION CANDIDATE
Solo después de evidencia suficiente. Nunca promoción automática a dinero real.

---

# 8. Regla de siguiente acción

AXXEL siempre debe elegir:

> **La tarea desbloqueada que reduzca el cuello de botella dominante sin violar gates.**

Hoy esa tarea es:

`REVIEW_G3_G4_BLOCKERS_UNDER_SEPARATE_AUTHORIZATION`

Solo tras evidencia del gate Foundation y aprobacion posterior:

`BUILD_CONTROL_TOWER_V1`


---

# 9. Principio de fundación compartida

`COLLECT ONCE, CERTIFY ONCE, REUSE MANY TIMES`

AXXEL no inicia cada proyecto desde cero.

Cada proyecto debe:
- reutilizar datos y capacidades existentes;
- identificar solo lo que falta;
- construir/certificar ese delta;
- devolver los nuevos activos reutilizables a la fundación común.

---

# 10. Future Intelligence Principles

These are future design rules, not current PHASE_1 work.

## Generalist first
Use a replaceable generalist model through a stable AXXEL interface. Memory, state, policies,
recipes and evidence remain outside the model.

## Compose before specialize
Reuse existing tools/capabilities before creating a specialist.

## Plan in subtasks, execute in actions
Control Tower/Planner chooses bounded subtasks; Agent Runtime executes locally.

## Reuse before acquire
Projects reuse certified datasets and prior experience before collecting new assets.

## Diversity over blind volume
Measure coverage/diversity, not only dataset size.

## Metadata only when it proves value
Context fields, instructions and metadata remain only if ablation tests show measurable lift.

## Low-quality experience is not certified evidence
Failed/noisy trajectories may help learning or diagnosis when provenance and quality are explicit,
but cannot contaminate certified research evidence.

---

# 11. Dependency Rule for Future Intelligence Work

Do NOT build Generalist Intelligence or Hierarchical Agent Control before:

```text
DATA ENGINE CERTIFIED
→ CONTROL TOWER FUNCTIONAL
→ OBSERVABILITY FUNCTIONAL
→ EVALUATOR FUNCTIONAL
→ EXPERIENCE ENGINE FUNCTIONAL
```

These future layers depend on the foundation; they do not replace it.

