# AGENTS

## AXXEL MASTER ARCHITECTURE — LECTURA OBLIGATORIA

Antes de realizar cualquier trabajo en este repositorio:

1. Leer `.axxel/master_architecture/README.md`
2. Leer `.axxel/master_architecture/00_START_HERE/AXXEL_MASTER_PLAN_V2.md`
3. Leer `.axxel/master_architecture/00_START_HERE/ARCHITECTURE_AUDIT.md`
4. Leer `.axxel/master_architecture/13_STATE/AXXEL_STATE.json`
5. Leer `.axxel/master_architecture/12_ROADMAP_BACKLOG/MASTER_ROADMAP.md`
6. Leer `.axxel/master_architecture/12_ROADMAP_BACKLOG/DETAILED_TASK_BACKLOG.md`

Después identificar obligatoriamente:

- fase actual;
- cuello de botella principal;
- tarea actual;
- siguiente tarea desbloqueada;
- dependencias;
- componentes protegidos;
- exit gate de la fase actual.

## REGLA MAESTRA

No reconstruir AXXEL desde cero.

La arquitectura existente es el baseline protegido.

Toda mejora debe ser aditiva por defecto y respetar:

OBSERVE
→ DOCUMENT
→ IMPLEMENT / SHADOW
→ TEST
→ VALIDATE
→ PROMOTE

No avanzar a fases futuras si la fase actual no ha pasado su exit gate.

No convertir nuevas ideas de arquitectura en componentes nuevos salvo que exista una necesidad operacional demostrable.

## PRIORIDAD ACTUAL

PHASE_1_FOUNDATION

Dominio prioritario:

DATA_INTEGRITY_AND_CERTIFICATION

Cuello de botella exacto:

SOURCE_INTEGRITY_AND_SESSION_GAP_CLASSIFICATION

Prioridad:

CERTIFY_XAUUSD_M1_DATA_INTEGRITY

Data Engine V1: IMPLEMENTED. Certificación: IN_PROGRESS. DATA_ENGINE_CERTIFIED=false.
Piloto: EXPLORATORY_ONLY. Control Tower bloqueado por el exit gate de Foundation.

La arquitectura futura no debe distraer ni bloquear esta prioridad.

---

## AXXEL EDGE DISCOVERY — REGLAS CIENTÍFICAS EXISTENTES

Leer primero:

1. `AXXEL_EDGE_DISCOVERY_MD/00_CORE/AGENT.md`
2. `AXXEL_EDGE_DISCOVERY_MD/00_CORE/MISSION.md`
3. `AXXEL_EDGE_DISCOVERY_MD/06_OPERATIONS/AUTONOMOUS_LOOP.md`

Nunca saltar validación para llegar a MQL5.

Machine Learning es parte del flujo científico, no un atajo:
usar solo features causales, particiones temporales y configuración pre-registrada.

En discovery / entrenamiento / calibración / selección solo se permite DEV.

`LOCKED_OOS` no se abre.

`VALIDATION` exige una ceremonia independiente.

Data Engine es la única entrada oficial de datos.

Leer:

`AXXEL_EDGE_DISCOVERY_MD/02_DATA/DATA_ENGINE.md`

antes de ingesta o consumo.

Discovery, ML y backtest solo consumen certificados elegibles.

Nunca abrir RAW o históricos sin certificar para sortear un bloqueo.

No corregir precios, gaps ni spreads automáticamente.

Mantener:

- RAW;
- lineage;
- falsaciones;
- Evidence Registry.

La suite usa fixtures sintéticos.

No inspeccionar holdouts reales ni siquiera para hashes.

---

## CONTRATO DE TRABAJO DEL AGENTE

Antes de modificar código:

1. inspeccionar implementación existente;
2. comprobar estado;
3. comprobar dependencias;
4. comprobar paths protegidos;
5. definir un cambio mínimo;
6. definir acceptance criteria.

Después de cada tarea:

1. ejecutar tests;
2. guardar evidencia;
3. registrar artefactos;
4. actualizar estado;
5. registrar fallos;
6. registrar aprendizajes;
7. registrar riesgos;
8. indicar siguiente acción recomendada.

Una tarea no está terminada solo porque el código compile.

Debe pasar sus acceptance criteria y producir evidencia.

---

## STOP CONDITIONS

Detenerse y reportar si:

- falta evidencia;
- el cambio amenaza un componente protegido;
- falla un test crítico;
- existe contradicción entre estado y repositorio;
- se requiere abrir LOCKED_OOS;
- se requiere saltar Data Engine;
- se requiere habilitar trading real;
- se intenta reducir un gate para obtener mejores resultados;
- se requiere borrar o reinterpretar evidencia histórica.

STOP es un resultado válido.

## MANTENIMIENTO DEL MASTER CANÓNICO

La fuente de verdad es `.axxel/master_architecture/`; el ZIP es derivado.
Después de cualquier cambio aprobado de arquitectura, estado, roadmap, gates,
contratos, ADR, fase, current_task o next_best_action, el agente debe ejecutar
`python scripts/package_master_architecture.py`, verificar el resultado y registrar
la ubicación y SHA256 del ZIP. No delegar esta regeneración manualmente en Alex.
El script crea una carpeta nueva en `reports/master_architecture_exports/` y nunca
sobrescribe snapshots históricos. Si falla, reportar el fallo y no declarar el
paquete actualizado. Aplicar también la política canónica de mantenimiento.
