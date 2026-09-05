# EXPERIENCE REPLAY

## Contrato vigente de datos

Replay solo reconstruye experiencias DEV certificadas y verificadas. El replay de JSON mixto está retirado; allow_locked no existe como autorización. La evidencia histórica sigue consultable sin reabrir datos protegidos.

Reglas y responsabilidades del componente experience replay.

## V1

Replay recupera exactamente un EXPERIENCE_ID y recalcula su SHA-256 canónico. El bucle de mercado verificó diez experiencias DEV, todas con hash válido, sin acceder a LOCKED_OOS.

## V2

El replay consulta Parquet por `EXPERIENCE_ID`, reconstruye el registro y vuelve a calcular `record_hash`. La recuperación de similares usa únicamente campos `state_*` y DEV por defecto. VALIDATION debe pedirse explícitamente; LOCKED_OOS además requiere una capacidad explícita (`allow_locked=True`). Dos ciclos V2 recuperaron y reprodujeron diez experiencias DEV, crearon episodios enlazados y consolidaron una memoria semántica con esos IDs.
