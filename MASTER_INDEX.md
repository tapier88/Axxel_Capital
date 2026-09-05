# Indice vigente

Entrada ejecutiva: [README](README.md). Fuente canonica: [master](.axxel/master_architecture/README.md).
Los indices cientificos siguientes conservan referencias historicas; datos y modelos no se publican.

# MASTER INDEX

## Contrato vigente de datos

Entrada de datos vigente: `src/data/engine.py`, `src/data/quality.py`, `config/data_engine_xauusd_m1_v1.json`, `scripts/run_data_engine.py`, `requirements-data-engine-lock.txt` y `tests/data_quality/test_data_engine.py`. Contrato: `AXXEL_EDGE_DISCOVERY_MD/02_DATA/DATA_ENGINE.md`. Los pipelines/adquisiciones V1/V2 enumerados abajo son referencias históricas, no comandos autorizados de ingesta. Sus lectores sin certificado están retirados.

Entrega ML: `reports/ML_INTEGRATION_REPORT.md`. Incidencia heredada de acceso a particiones y corrección: `reports/ML_PARTITION_ACCESS_INCIDENT.json`. No borrar ni confundir con accesos del runner ML, que son exclusivamente DEV.

## Sistema integrado: Machine Learning

ML nativo: `src/ml/data.py`, `models.py`, `experiment.py`; entrada oficial `DiscoveryEngine.run_ml_candidate()`. Configuración `config/ml_xauusd_0830_v1.json`; runner `scripts/run_ml_experiment.py`; pruebas `tests/ml/test_ml_pipeline.py`; modelos `models/ml-xauusd-0830-v1/`; evidencia `reports/evidence/ML_XAUUSD_0830_V1.json`.

Índice maestro de la documentación. Mantener actualizado cuando se agreguen o retiren módulos.

## Orden de lectura

1. `00_CORE`: misión, autonomía, aprendizaje, fallos y escalamiento.
2. `01_ARCHITECTURE`: componentes, flujo, experiencia, memoria, retrieval, value y separación MT5.
3. `02_DATA`: contratos y persistencia de experiencia.
4. `03_RESEARCH`: hipótesis, experimentos, incertidumbre y priorización.
5. `04_VALIDATION`: barreras adversariales requeridas antes de toda promoción.
6. `05_EXECUTION`: límites de ejecución; V0 no opera.
7. `06_OPERATIONS`: bucle, estado, recuperación y checkpoints.
8. `11_MEMORY` y `12_VALUE_MODEL`: aprendizaje reutilizable V0.
9. `07_LOGS` a `10_PROMPTS`, `13_HYPOTHESES`, `14_EXPERIMENTS` y `15_KNOWLEDGE`: soporte documental.

## Implementación V0

- Orquestación: `src/orchestrator/agent_loop.py`, `state_machine.py`.
- Investigación: `src/research/hypothesis_engine.py`, `experiment_engine.py`, `uncertainty_engine.py`, `skeptic_engine.py`.
- Experiencia: `src/experience_store/repository.py`, `store.py`.
- Memoria: working, episodic, semantic, long-term, retrieval, scoring y consolidation en `src/memory/`.
- Value: `src/value/information_value.py`, `research_value.py`.
- Ejecución segura: `src/execution/execution_engine.py`.
- Operación: `scripts/run_autonomous_loop.py`, `scripts/consolidate_memory.py`.
- Pruebas: `tests/test_system_v0.py`.
- Auditoría y cambios: `reports/ARCHITECTURE_AUDIT_V0.md`.
- Datos reales y Experience Store: `reports/PROMPT_2_MARKET_EXPERIENCE_REPORT.md`.
- Schema ejecutable: `config/market_experience_schema_v1.json`.
- Pipeline: `src/data/pipeline.py`; almacenamiento/retrieval: `src/experience_store/market_store.py`.
- Adquisición reproducible: `scripts/acquire_marketdata.py`; rebuild: `scripts/rebuild_experience_store.py`.
- Pruebas de datos: `tests/data_quality/test_market_pipeline.py`.
- Adquisición MT5 M1/ticks V2: `src/data/mt5_acquisition.py`, `scripts/acquire_mt5_gold_v2.py`.
- Auditoría escalable V2: `src/data/quality_v2.py`, `scripts/audit_gold_v2.py`.
- Experience Store Parquet V2: `src/data/pipeline_v2.py`, `src/experience_store/parquet_store.py`.
- Política temporal congelada: `config/partitions_gold_m1_v2.json`.
- Contrato V2: `config/market_experience_schema_v2.json`.
- Ciclo operativo V2: `scripts/run_market_v2_iteration.py` y `AutonomousLoop.run_market_v2_iteration()`.
- Pruebas V2: `tests/data_quality/test_market_v2.py`.
- Informe y auditoría: `reports/PROMPT_3_XAUUSD_M1_TICKS_REPORT.md`, `reports/gold_m1_ticks_quality_v2.json`.
- Registro estadístico y pre-registro: `src/research/evidence_registry.py`, `hypotheses/evidence_registry.json`.
- Motor de evidencia: `src/validation/evidence_engine.py`; bootstrap, permutación, FDR, costes, estabilidad, OOS y skeptic en `src/validation/`.
- Batería congelada: `config/calibration_hypotheses_v1.json`; ejecución: `scripts/run_evidence_calibration.py`.
- Evidencia Prompt #4: `reports/evidence/PROMPT_4_CALIBRATION_BATTERY.json` y `reports/PROMPT_4_EVIDENCE_ENGINE_REPORT.md`.
- Pruebas estadísticas: `tests/validation/test_evidence_engine.py`.
- Discovery autónomo: `src/research/discovery_engine.py`, `hypothesis_generator.py`, `hypothesis_graph.py`.
- Research Value V2: `src/value/research_value.py`; límites reproducibles: `config/discovery_limits_v1.json`.
- Diagnósticos DEV: `src/research/volatility_diagnostic.py`, `intraday_structure.py`.
- Campaña: `scripts/run_discovery_campaign.py`; evidencia: `reports/evidence/PROMPT_5_DISCOVERY_CAMPAIGN.json`.
- Grafo persistente: `hypotheses/graph.json`; pruebas: `tests/research/test_discovery_engine.py`.
- Informe Discovery V1: `reports/PROMPT_5_DISCOVERY_REPORT.md`.
- Ceremonia confirmatoria: `src/validation/confirmation.py`, `scripts/run_validation_ceremony.py`.
- Manifiesto y protocolo inmutables: `reports/validation/VALIDATION_CEREMONY_MANIFEST.json`, `VALIDATION_CEREMONY_PROTOCOL.json`.
- Resultado confirmatorio: `reports/validation/PROMPT_6_VALIDATION_CEREMONY.json`.
- Estado de autorización única: `state/validation_ceremony_state.json`; pruebas: `tests/validation/test_confirmation.py`.
- Informe Prompt #6: `reports/PROMPT_6_VALIDATION_REPORT.md`.
- Entrega Prompt #6 exacta de 40 puntos: `reports/PROMPT_6_VALIDATION_REPORT_40_POINT.md`.
- Cuarentena post-validation: `reports/validation/POST_VALIDATION_OBSERVATIONS.json` y `quarantine_post_validation_observation()`.

Los módulos enumerados arriba tienen implementación y pruebas. Los demás módulos Python y documentos breves permanecen como esqueletos o contratos parciales; su presencia no significa capacidad operativa.
