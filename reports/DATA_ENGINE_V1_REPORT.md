# AXXEL Data Engine V1 — entrega y piloto

Data Engine está integrado como frontera obligatoria de datos dentro de `src/data`, reutilizando Experience Store, features, outcomes y consumidores científicos existentes. El piloto se procesó, pero **no es elegible para investigación**.

## Cambios de código y arquitectura

- `src/data/engine.py`: RAW direccionado por SHA256, publicación exclusiva, bronze/silver, manifiesto final, snapshots de transformaciones, comprobación de integridad, consultas DuckDB, certificación y exportación gold M1.
- `src/data/quality.py`: esquema Pandera, comprobaciones temporales/OHLC/precio/spread/volumen/símbolo/broker, gaps, stale runs y saltos; hallazgos por fila y score explícito.
- `src/experience_store/parquet_store.py`: exige certificado y registro gold coincidente; comprueba rutas antes de leer. JSON mixto retirado. `DevOnlyMLData` verifica certificación antes incluso de calcular el checksum del fichero de mercado.
- Reutilización del derivador causal M1; warmup discontinuo se vuelve nulo y no se importan ticks de otras particiones para calcular costes. No se reconstruyen las experiencias antiguas bajo su misma identidad.
- Campañas económicas y Discovery usan el store certificado. Skeptic obtiene calidad del certificado correspondiente, no del informe global anterior. Se retiró un hash indirecto de CSV externos.
- Las rutas antiguas de ingesta/publicación mixta y auditoría bruta fallan de forma explícita; los comandos de adquisición retirados paran antes de conectar. V1 recibe Parquet OHLCV acotado; otros adaptadores no se presentan como implementados.

## Auditoría y decisiones

La adquisición antigua deduplicaba antes de preservar RAW; los builders calculaban features/labels antes de separar particiones; el lector JSON cargaba particiones mixtas; la calidad no era una condición obligatoria y algunos consumidores usaban informes globales. Había conversiones y aliases hardcoded, reglas de gaps sin calendario comprobado y metadatos de versión insuficientes para identificar cambios de transformación.

Se escogió Pandera sobre un segundo framework Great Expectations; de GX se reutiliza la separación de validaciones/resultados, no su infraestructura. Qlib y Trading Strategy aportaron ejemplos de checks, no reglas de limpieza aplicables automáticamente al oro. Medallion se aplica como separación local de responsabilidades. Fuentes oficiales y decisiones detalladas: [Data Engine](../AXXEL_EDGE_DISCOVERY_MD/02_DATA/DATA_ENGINE.md).

## Piloto XAUUSD M1

- Dataset: `DE1-658ff72ef8932e5b4d50118751d039fc11015010ec6f1101c3dce81805b58706`.
- Fuente: XM Global Limited, GOLD/XAUUSD, histórico previamente transformado.
- Cobertura realmente leída: primer rowgroup, 2015-01-02 08:06 UTC a 2017-12-19 15:00 UTC; 1.048.576 velas.
- Se inspeccionó el footer de la fuente mixta para delimitar los grupos. Los otros tres payloads, incluyendo grupos que mezclan DEV/VALIDATION/OOS, no se abrieron. No se recalculó el hash completo de esa fuente ni se abrió la muestra de ticks 2024.
- Resultado: `EXPLORATORY_ONLY`, score **89,7073/100**, cero velas eliminadas.
- Hallazgos: 2.679 gaps REVIEW; 249 spreads cero, 146 alertas stale y un salto KEEP_FLAGGED. Son alertas de filas, no necesariamente 146 episodios independientes de stale prices.
- Cobertura: tick volume positivo 100%; real volume positivo 17,0446%. El spread de barras no acredita costes reales ni slippage ejecutado.
- No hubo REJECT estructural detectado; aun así, procedencia original incompleta y gaps sin contrastar impiden la elegibilidad científica. Un score alto no elimina esos gates.

Artefactos: [calidad](../data/engine/datasets/DE1-658ff72ef8932e5b4d50118751d039fc11015010ec6f1101c3dce81805b58706/quality.json), [manifiesto](../data/engine/datasets/DE1-658ff72ef8932e5b4d50118751d039fc11015010ec6f1101c3dce81805b58706/manifest.json), [verificación](DATA_ENGINE_V1_VERIFICATION.json).

## Pruebas y reproducción

`python -m pytest tests -q`: **148 passed**, 18,28 s. La suite usa datos sintéticos para mercado: reproducibilidad, idempotencia, corrupción de RAW/derivados, hashes, anomalías, DST, causalidad, límites, registro gold, ML, backtest económico y negativas de acceso. Se sustituyeron las antiguas pruebas que abrían artefactos reales y las que afirmaban un bypass OOS.

El piloto final se ejecutó dos veces con el mismo ID y se verificaron todos los hashes del manifiesto. El intento de generar gold falló con `PermissionError: Dataset cannot enter research: EXPLORATORY_ONLY`, como exige la política. No se ejecutó un experimento científico ML sobre este piloto.

```powershell
python -m pip install -e ".[data-engine,ml]"
python -m pip install -r requirements-data-engine-lock.txt
python -m pytest tests -q
python scripts/run_data_engine.py --config config/data_engine_xauusd_m1_v1.json
```

La comprobación global `pip check` detecta conflictos de rembg/fastapi ajenos al runtime probado de AXXEL. No se han modificado esos paquetes. Se recomienda un entorno virtual separado para instalar los locks de AXXEL.

## Documentación y límites

README, AGENTS, CORE, arquitectura, flujo, adquisición/normalización/calidad/inventario, schemas, Experience Store, Discovery, replay, validación, Skeptic, operaciones, configuración e índice maestro describen la frontera obligatoria. El inventario exacto está en el JSON de verificación. Los informes históricos y la falsación ML se conservaron.

Límites explícitos: V1 solo expone DEV; gold es M1, aunque certifica barras M5; los adaptadores live/ticks/CSV y la capacidad de ceremonia VALIDATION no están implementados. La ingesta en memoria se limita a dos millones de filas; no es un motor out-of-core ilimitado. Hashes, rutas y pruebas protegen las APIs oficiales, no contra un propietario del sistema operativo que reescriba código y certificados.

## Qué sigue

Contrastar los gaps con calendario histórico verificable del broker y obtener una fuente DEV original preservada antes de transformar, con evidencia del contrato y costes. Si cambia la política por nueva evidencia, congelar otra versión y registrar la justificación; no modificar este certificado ni bajar requisitos para habilitar el piloto. Mantener la incidencia previa de OOS y la falsación direccional ML como hechos históricos.
