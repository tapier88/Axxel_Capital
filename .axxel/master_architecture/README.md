# AXXEL CAPITAL — MASTER ARCHITECTURE V2

Fuente canónica: este directorio. Mantenimiento y regeneración del ZIP a cargo del
agente: `00_START_HERE/MASTER_PACKAGE_MAINTENANCE.md`.

**Estado del paquete:** Arquitectura de evolución aditiva  
**Objetivo:** extender AXXEL sin romper, borrar, reinterpretar ni simplificar la arquitectura validada existente.  
**Rol humano:** `HUMAN_ON_THE_LOOP`  
**Estado actual:** `PHASE_1_FOUNDATION`  
**Cuello de botella actual:** `G3_HISTORICAL_ROUTE_AND_G4_XM_FORWARD_QUALIFICATION`  
**North Star:** `REPRODUCIBLE_RISK_ADJUSTED_NET_EDGE`

---

## Qué es este paquete

Este directorio define:

1. **Dónde está AXXEL hoy.**
2. **Dónde se encuentra el agente dentro de la arquitectura.**
3. **Qué capacidades existen, cuáles están degradadas y cuáles faltan.**
4. **A dónde queremos llegar.**
5. **Cómo debe evolucionar el sistema sin destruir lo que ya funciona.**
6. **Qué tareas deben ejecutarse, en qué orden y con qué criterios de aceptación.**
7. **Cómo convertir resultados, errores e intervenciones humanas en experiencia reutilizable.**
8. **Cómo medir autonomía, confiabilidad, throughput, coste y velocidad de mejora.**
9. **Cómo detectar gaps de proceso o arquitectura.**
10. **Cómo proponer, probar, validar, promover o revertir mejoras.**

---

## Regla constitucional

> **AXXEL NO REEMPLAZA LO VALIDADO POR DEFECTO. AXXEL EVOLUCIONA DE FORMA ADITIVA.**

Ningún componente existente puede ser eliminado, sobrescrito, simplificado o reinterpretado sin:

`EVIDENCE → TEST → SHADOW/SANDBOX → CHALLENGER → VALIDATION → ROLLBACK PLAN → PROMOTION`

Toda nueva capacidad empieza fuera del camino crítico de producción.

---

## Ruta de lectura para Codex / agente

Leer en este orden:

1. `00_START_HERE/AXXEL_MASTER_PLAN_V2.md`
2. `00_START_HERE/AGENT_POSITION_AND_MISSION.md`
3. `01_CURRENT_SYSTEM/CURRENT_STATE.md`
4. `01_CURRENT_SYSTEM/PROTECTED_BASELINE.md`
5. `02_TARGET_ARCHITECTURE/TARGET_ARCHITECTURE.md`
6. `12_ROADMAP_BACKLOG/MASTER_ROADMAP.md`
7. `12_ROADMAP_BACKLOG/DETAILED_TASK_BACKLOG.md`
8. `13_STATE/AXXEL_STATE.json`
9. `13_STATE/CAPABILITY_MATRIX.json`

Después de leerlos, el agente debe seleccionar **solo la siguiente tarea desbloqueada**.

---

## Regla de ejecución

El agente nunca debe interpretar este paquete como permiso para reconstruir el proyecto desde cero.

Debe:

- inspeccionar;
- preservar;
- medir;
- documentar;
- extender;
- validar;
- comparar;
- promover solo si mejora;
- revertir si degrada.








## Regla para futuras mejoras

Antes de añadir cualquier componente, leer `00_START_HERE/ARCHITECTURE_DECISION_RULES.md`.

## Generalist Intelligence

Diseño consolidado en `15_GENERALIST_INTELLIGENCE/GENERALIST_INTELLIGENCE_ARCHITECTURE.md`.

## Agent Control

Diseño operativo en `18_CONTEXT_AND_HIERARCHICAL_CONTROL/AGENT_CONTROL_LOOP.md`.

## Auditoría lógica

Leer `00_START_HERE/ARCHITECTURE_AUDIT.md` para ver el camino crítico, dependencias y riesgos actuales.
