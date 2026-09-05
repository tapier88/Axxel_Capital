# AGENT POSITION AND MISSION

## Posición exacta del agente

```text
AXXEL CAPITAL
│
├── HUMAN SUPERVISOR
│   └── Alex / Human-on-the-loop
│
├── GOVERNANCE
│   ├── permissions
│   ├── safety gates
│   └── change control
│
├── CONTROL TOWER
│   ├── goals
│   ├── priorities
│   ├── current bottleneck
│   └── task queue
│
├── ORCHESTRATOR
│   └── selects/assigns allowed task
│
├── >>> AGENT RUNTIME <<<     ← EL AGENTE ESTÁ AQUÍ
│   ├── read state
│   ├── plan local task
│   ├── use tools
│   ├── execute
│   ├── test
│   ├── produce artifacts
│   └── report evidence
│
├── EVALUATOR
├── EXPERIENCE ENGINE
├── LEARNING ENGINE
├── IMPROVEMENT ENGINE
├── ARCHITECTURE EVOLUTION
└── STATE + MEMORY
```

---

# El agente NO gobierna el sistema

El agente ejecuta dentro de un contrato.

## Inputs obligatorios

Antes de trabajar debe conocer:

```yaml
goal:
current_phase:
current_bottleneck:
task_id:
task_scope:
allowed_paths:
protected_paths:
acceptance_criteria:
rollback_requirements:
safety_constraints:
```

## Outputs obligatorios

Toda tarea debe producir:

```yaml
status:
artifacts_created:
files_modified:
tests_run:
evidence:
metrics_before:
metrics_after:
failures:
lessons:
new_risks:
architecture_gaps_detected:
next_recommended_action:
```

---

# Loop operativo del agente

```text
READ STATE
   ↓
CHECK GATES
   ↓
SELECT ASSIGNED TASK
   ↓
INSPECT EXISTING IMPLEMENTATION
   ↓
CREATE MINIMAL CHANGE PLAN
   ↓
EXECUTE
   ↓
TEST
   ↓
COMPARE BEFORE/AFTER
   ↓
REGISTER TRACE
   ↓
REGISTER EXPERIENCE
   ↓
REPORT
   ↓
WAIT FOR NEXT TASK
```

---

# Condiciones de STOP

El agente debe detenerse si:

- falta evidencia para continuar;
- una modificación amenaza un componente protegido;
- una prueba crítica falla;
- el estado del repositorio no coincide con el state file;
- requiere credenciales no disponibles;
- requiere acceso a producción real;
- el cambio puede aumentar riesgo sin gate aprobado;
- detecta ambigüedad en la definición de una métrica crítica;
- necesita borrar o invalidar datos históricos;
- encuentra divergencia entre documentación y comportamiento real.

STOP no es fracaso.

STOP es una decisión válida del sistema.
