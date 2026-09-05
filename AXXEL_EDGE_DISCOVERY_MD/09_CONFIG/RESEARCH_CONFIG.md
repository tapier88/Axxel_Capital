# RESEARCH CONFIG

## Contrato vigente de datos

La configuración de datos piloto es `config/data_engine_xauusd_m1_v1.json`; el calendario congelado existente permanece intacto. Las recetas Data Engine incorporan versiones de dependencias y hashes de código. No modificar el pre-registro ML histórico para apuntarlo a un resultado distinto.

Los experimentos ML se configuran en JSON inmutable. `config/ml_xauusd_0830_v1.json` fija dataset, población, horizonte, label ATR, folds, seeds, CPU/hilos, parámetros de los tres boosters, umbrales de decisión, Skeptic y promoción. Cambiarlo crea otra hipótesis/versión; nunca se sobrescribe después del resultado.
