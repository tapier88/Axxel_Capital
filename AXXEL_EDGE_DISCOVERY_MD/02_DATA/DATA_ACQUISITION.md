# DATA ACQUISITION

La única ingesta oficial es `DataEngine.ingest_parquet`, con fuente OHLCV M1/M5 acotada a DEV, timezone explícita y contrato de broker/símbolo/point/BAR_OPEN. La fuente se preserva antes de ordenar, deduplicar o validar. Cada transformación posterior tiene lineage.

Comando: `python scripts/run_data_engine.py --config config/data_engine_xauusd_m1_v1.json`.

La adquisición histórica MT5 mezclaba 2015–2024 y eliminaba duplicados antes de RAW; por eso su origen se clasifica como legacy transformado. El piloto solo exporta bloques enteramente DEV. Los comandos antiguos MCP, MT5 mixto y publicación de ticks están deshabilitados antes del acceso de red. Nuevos adaptadores deberán preservar la respuesta original antes de normalizar y exigir una política temporal compatible.

Contrato completo: [Data Engine](DATA_ENGINE.md). No usar la muestra de ticks 2024 para research DEV.
