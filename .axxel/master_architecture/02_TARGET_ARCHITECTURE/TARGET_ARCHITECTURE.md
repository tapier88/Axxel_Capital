# TARGET ARCHITECTURE

## Arquitectura objetivo

```text
HUMAN SUPERVISOR
      ↓
GOVERNANCE
      ↓
CONTROL TOWER
  goals | state | bottleneck | task queue
      ↓
PLANNER / ORCHESTRATOR
  dependencies | next subtask | budgets
      ↓
CONTEXT COMPILER
  state | memory | task | constraints
      ↓
GENERALIST INTELLIGENCE LAYER  [future]
  model abstraction | capability composition
      ↓
AGENT RUNTIME
  research | coding | testing | tools
      ↓
EXECUTION ─────────────→ TELEMETRY
      ↓                    ↓
      └──────── EVALUATOR ─┘
                  ↓
           EXPERIENCE STORE
                  ↓
           LEARNING ENGINE
                  ↓
          IMPROVEMENT ENGINE
             ↙          ↘
       PROCESS GAP   ARCHITECTURE GAP
             ↘          ↙
              CHALLENGER
                  ↓
        VALIDATE / REJECT / PROMOTE
                  ↓
                STATE

DATA ENGINE / SHARED DATA FOUNDATION
feeds certified data, provenance and reusable assets across the system.
```

---

# Subsistemas obligatorios

## 1. Control Tower
Fuente única de verdad sobre qué debe hacer AXXEL.

## 2. Agent Runtime
Ejecutor reemplazable. Nunca fuente única de verdad.

## 3. Evaluator
Decide si una salida es válida según métricas y gates.

## 4. Experience Store
Convierte cada ejecución en experiencia estructurada.

## 5. Learning Engine
Extrae lecciones recurrentes.

## 6. Improvement Engine
Encuentra el cuello de botella de mayor impacto.

## 7. Architecture Gap Detector
Distingue:
- error local;
- error de proceso;
- falta de herramienta;
- falta de capacidad estructural.

## 8. Champion/Challenger
Impide modificar procesos validados sin comparación.

## 9. Governance
Controla permisos y promociones.

## 10. Mission Control
Hace visible el sistema al supervisor.
