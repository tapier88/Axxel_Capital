# Estado del proyecto

| Área | Estado vigente |
|---|---|
| Fase | PHASE_1_FOUNDATION |
| Cuello de botella | G3_HISTORICAL_ROUTE_AND_G4_XM_FORWARD_QUALIFICATION |
| Track A / G3 | NOT_ESTABLISHED |
| Track B V1 | BLOCKED_AND_REVOKED_FOR_QUALIFICATION; evidencia preservada |
| Track B V2 | IMPLEMENTED_AWAITING_START_APPROVAL; readiness BLOCKED |
| V2 activation / T0 / G4 | false / null / false |
| XM legacy / HistData | EXPLORATORY_ONLY / EXPLORATORY_ONLY |
| Data Engine | IMPLEMENTED; DATA_ENGINE_CERTIFIED=false |
| Control Tower | BLOCKED; no avance a PHASE_2 |

## Hitos comprobados

Data Engine V1 implementado con custodia, hashes, calidad, manifests y lectura autorizada.
FOUNDATION_SCOPE_READINESS_V1 implementado en SHADOW: G1 de implementación/pruebas,
G5 y G6 en SHADOW; esto no es certificación científica. ADR-FOUNDATION-001 aprobado.
Track B V2 aceptado con 44 pruebas integradas dentro de 326 pruebas de aquella entrega.
El mantenimiento del ZIP añadió cinco pruebas. Resultado de esta publicación en
[verificación](../reports/public_baseline/VERIFICATION_FINAL.json); los conteos anteriores
son hitos históricos, no resultados nuevos inferidos.

Track A necesita una ruta histórica documentada y aprobada, no otra compra por defecto.
Track B V1 inició en 2026-09-04T19:18:39.974001Z y fue revocado; nunca se cambia a PASS.
La causa operacional confirmada fue suspensión System Idle, amplificada por reinicios
del monitor. Se preservan 2676 artefactos V1 localmente, sin publicar RAW.
V2 mantiene activation=false, T0=null y configuración congelada. Readiness está bloqueado
por energía, verificación de símbolo sin mercado, binding/ceremonia de T0, supervisor,
sincronización de storage y throughput de reconciliación prolongada.

## Incidentes y límites

Una suite histórica abrió indebidamente LOCKED_OOS: el bypass se eliminó y el incidente
permanece en [ML_PARTITION_ACCESS_INCIDENT](../reports/ML_PARTITION_ACCESS_INCIDENT.json).
No afirmar que ese holdout nunca se abrió. Esta publicación no lo lee ni lo hashea.
XM/HistData tienen carencias de procedencia/reloj/sesiones; ninguna limpieza otorga elegibilidad.
Los resultados históricos de VALIDATION son decisiones consumidas y preservadas, no una
nueva ceremonia ni permiso para reutilizar datos. Próxima tarea: revisar blockers G3/G4,
con aprobación separada de cualquier cambio operacional; no se ejecuta en esta entrega.


## Revisión de arranque Track B V2 — 2026-09-07

Readiness: **TRACK_B_V2_START_READINESS_BLOCKED**. Suite completa: 344 passed.
Escala: 279 lotes medidos de 384 previstos, pico 47,139 s; ensayo interrumpido
por incumplimiento de cadencia. Métricas finales y recuperación a escala incompletas.
No cambia código/configuración de producción ni se crea T0. Próxima acción:
REVIEW_TRACK_B_V2_OPERATIONAL_GAPS_FOR_AUTHORIZATION.
[Informe](TRACK_B_V2_START_READINESS_REPORT.md) y [checklist](TRACK_B_V2_START_CHECKLIST.md).
