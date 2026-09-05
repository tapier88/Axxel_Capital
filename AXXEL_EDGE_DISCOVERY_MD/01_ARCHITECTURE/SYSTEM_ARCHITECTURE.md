# SYSTEM ARCHITECTURE

## Contrato vigente de datos

Data Engine (`src/data/engine.py`, `quality.py`) precede a Experience Store y certifica fuente/RAW/bronze/silver/gold. Discovery, ML y simulación económica usan sus certificados a través del store existente; memoria, grafo, evidencia y value no cambian de propietario. No hay lector científico de RAW. Contrato y límites: `02_DATA/DATA_ENGINE.md`.

Referencias de las APIs utilizadas: [XGBoost](https://github.com/dmlc/xgboost), [LightGBM](https://github.com/microsoft/LightGBM), [CatBoost](https://github.com/catboost/catboost). Se fijan CPU, semillas, hilos, early stopping y serialización nativa; las versiones probadas están en `requirements-ml-lock.txt` y en cada reporte.

## Arquitectura integrada

`orchestrator` coordina `research`, `ml`, `validation`, `memory`, `value` y, solo tras promoción, `execution`. ML no tiene registro ni dataset propios: consume un candidato del Evidence Registry, lee exclusivamente DEV mediante `DevOnlyMLData`, reutiliza walk-forward y devuelve evidencia al mismo registro, grafo y carpeta de reportes.

`src/ml/data.py` fija frontera causal, features y labels; `models.py` normaliza las APIs CPU de XGBoost, LightGBM y CatBoost; `experiment.py` ejecuta folds, calibración, regresiones MFE/MAE, ensemble, economía, Skeptic y persistencia. Los artefactos nativos viven en `models/<experiment_id>/` con manifiesto, versiones y orden de features.

La dirección es `orchestrator/research → ml → experience_store/validation/value`. ML no importa ejecución, broker ni MQL5. `VALIDATION` requiere ceremonia independiente y `LOCKED_OOS` no es una capacidad disponible durante investigación.
