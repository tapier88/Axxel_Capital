# TIMEZONE RULES

## Contrato vigente de datos

Data Engine exige timestamps timezone-aware y semántica BAR_OPEN. Rechaza importaciones ambiguas; la normalización explícita prueba DST ambiguo/no existente sin inferirlo. UTC es el eje de particiones y America/Bogota la presentación de sesiones; ningún ajuste de horario se aprende de OOS.

Especificación de timezone rules.

## V1

Todo timestamp de barra fuente debe ser timezone-aware y se normaliza a UTC. Cada punto de decisión guarda `timestamp_utc` y `timestamp_cot` mediante `zoneinfo/America_Bogota`. La ventana es 08:00–12:30 COT; el raw completo y el contexto previo permanecen intactos.

En V2, los segundos/milisegundos POSIX de MT5 se convierten explícitamente a UTC. La decisión de una barra M1 ocurre un minuto después de su timestamp de apertura. America/Bogota no usa DST; no se infiere ni corrige silenciosamente el horario del broker.
