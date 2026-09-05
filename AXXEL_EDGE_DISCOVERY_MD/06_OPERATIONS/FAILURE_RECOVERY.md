# FAILURE RECOVERY

## Contrato vigente de datos

Data Engine publica artefactos exclusivos y el manifiesto al final. Repetir la misma receta es idempotente; discrepancias de hashes bloquean la lectura. No borrar ni sobrescribir RAW para reparar una ejecución: crear una nueva versión con lineage.

Procedimiento operativo para failure recovery.
