# Gaps y blockers

| Prioridad | Gap | Evidencia necesaria para cierre |
|---|---|---|
| CRITICAL | G3 NOT_ESTABLISHED | Producto/rango útil, derecho/acceso/entrega, originales, provenance, semántica temporal e instrumento, calendario y plan de custodia documentados; expediente aprobado conforme ADR §3.3. Mencionar un proveedor no basta. |
| CRITICAL | G4 false | V2 con preflight y arranque autorizados; ≥5 sesiones completas, cierre/reapertura semanal y rollover; UTC/contrato/RAW/incidentes/recovery auditables; revisión humana del intervalo. Tests sintéticos no sustituyen cualificación. |
| CRITICAL | DATA_ENGINE_CERTIFIED=false | G1…G6 revisados y al menos un certificado A histórico elegible, consumers/capacidades probados y alcance B con procedencia; ADR §6.1. |
| HIGH | Operación V2 | Energía no suspendible aprobada, storage sin sync aprobado, símbolo metadata-only, binding/T0 durables y supervisor revisados; throughput sostenido demostrado. |
| HIGH | Límites históricos | Fuente/reloj/sesiones/costes de XM e HistData no acreditados; conservar EXPLORATORY_ONLY y falsaciones. |
| HIGH | Holdout histórico | Incidente preservado, no reutilizar ni afirmar nunca abierto; aprobación científica independiente de cualquier futuro uso. |
| MEDIUM | Reproducción | Locks de versiones sin hashes transitivos; dependencia de evidencia documental local seleccionada; Windows crash tests requieren Windows. |
| MEDIUM | Mantenimiento documental | Matrices mezclaban módulos V0 y capacidades futuras; se explicita alcance y se conservan snapshots previos locales. |
| FUTURE | Control/observabilidad/aprendizaje | Dependen del gate de Foundation y de capas precedentes. No construir ahora. |

No se compran datos, contactan proveedores o cambian parámetros operacionales en esta tarea.
La configuración congelada V2 sigue intacta; su preregistro de readiness no es autorización.
