# PROMPT #3 — XAUUSD M1/Ticks y Experience Store V2

Fecha de construcción: 2026-09-03 UTC. Resultado: base real, versionada, auditable y operativa en `RESEARCH_ONLY`. No se ejecutaron órdenes ni se evaluó un edge.

## 1. Fuentes encontradas

- Proyecto: dataset público XAUUSD H1 V1 ya existente; se preservó sin mezclar.
- Terminal MT5 conectado: símbolo exacto `GOLD`, equivalente internacional XAUUSD, broker `XM Global Limited`, servidor `XMGlobal-MT5 6`; ofrece M1 desde 2001-06-04 y ticks bid/ask.
- MCP MarketData público: resolución mínima H1; insuficiente para este objetivo.
- Archivos históricos del terminal: `XAUUSD_Deep_History.csv` y `XAUUSD_20Y_History.csv`, ambos diarios; no seleccionados.

## 2. Fuente seleccionada

API oficial Python de MetaTrader 5 sobre el terminal conectado, solo lectura. M1 y ticks permanecen separados:

- `MT5-XMGLOBAL-GOLD-M1-V1`
- `MT5-XMGLOBAL-GOLD-TICKS-SAMPLE-V1`

## 3–5. Cobertura y volumen

- M1 solicitado: 2015-01-01 a 2024-12-31. Cobertura efectiva: 2015-01-02 08:06 UTC a 2024-12-31 20:00 UTC.
- Barras M1: 3.532.606.
- Ticks: 56.013, muestra acotada 2024-01-02 13:00:00.321 a 18:29:59.909 UTC. No representa historia completa de ticks.

## 6–7. Calidad y gaps

No hay duplicados, desorden temporal, nulls, OHLC inválido, precios no positivos, spreads negativos ni violaciones de dos decimales en M1. En ticks no hay duplicados exactos, desorden, bid/ask no positivo, `bid > ask`, spread negativo o cero. Ningún error bloqueante.

M1 contiene 5.493 saltos temporales mayores a un minuto, sin rellenar: 527 candidatos de fin de semana/multidía, 1.994 candidatos de pausa diaria (30–180m) y 2.911 gaps cortos de 2–29m. El mayor es 4.868m. Hay 39 sesiones de investigación incompletas, 15.944 candidatos a barra sintética, 620 barras con spread cero y 8.461 movimientos candidatos a revisión con umbral robusto 0,143439 %. Estas categorías son banderas, no errores declarados. UTC es la base; America/Bogota no usa DST.

Detalle reproducible: `reports/gold_m1_ticks_quality_v2.json`.

## 8–9. Spread y cost model

El M1 trae spread por barra. La muestra tick trae bid/ask real: mediana 33 puntos, p95 40, rango 26–78. WAIT cuesta cero. LONG/SHORT usan `REAL_TICK_COST` cuando existen quotes de entrada/salida dentro de tolerancia; en el resto, `PROXY_COST` usa spread de barra con punto 0,01 y reconoce que el gráfico es bid-based. Slippage no disponible permanece null, nunca se supone cero. Se generaron 2.166 etiquetas horizonte con coste tick real; el resto aplicable usa proxy.

## 10. Particiones congeladas

La política se escribió antes de analizar outcomes y está congelada en `config/partitions_gold_m1_v2.json`:

- DEV: 2015-01-01 a 2019-12-31.
- VALIDATION: 2020-01-01 a 2022-12-31.
- LOCKED_OOS: 2023-01-01 a 2024-12-31.

Los límites no se movieron. Cada partición es un archivo distinto; discovery abre solo DEV. LOCKED_OOS requiere acceso explícito.

## 11–14. Sesiones, experiencias, tamaño y formato

- Sesiones 08:00–12:30 America/Bogota: 2.580 (DEV 1.289; VALIDATION 775; LOCKED_OOS 516).
- Experiencias: 2.097.177 (DEV 1.047.684; VALIDATION 629.985; LOCKED_OOS 419.508).
- Tamaño del Experience Store V2: 1.003.448.425 bytes (aprox. 957 MiB), incluido manifest.
- Formato: Parquet + Zstandard para datos; JSON para manifiestos, índices, estados, memoria y provenance.
- Versión: `DATASET-V2-e4a8cc6b19c1ae75ddc74bbe`; esquema `market-experience-v2`.

Cada minuto elegible produce WAIT/LONG/SHORT contrafactuales. STATE es causal; OUTCOME contiene future return, excursiones, MFE, MAE y volatilidad realizada a 5/15/30/60m. Un outcome queda null si el horizonte exacto cruza un gap.

## 15–17. Pruebas, leakage y limitaciones

Pasan 27/27 pruebas. Cubren la V0/V1 y, para V2, hashes de fuentes/archivos, contrato temporal, horizontes exactos, costes, aislamiento de particiones, bloqueo OOS, reconstrucción Parquet y replay.

Leakage: `state_max_source_timestamp_utc < decision_timestamp_utc`; los campos futuros están bajo prefijos `label_`/`outcome_` y no participan en retrieval. La búsqueda similar V2 abre solo DEV. Dos ciclos autónomos registraron `partitions_accessed=[DEV]` y `locked_oos_accessed=false`.

Limitaciones: ticks solo para una sesión; la mayor parte del coste es proxy; no hay slippage observado; gaps y candidatos sintéticos no se imputaron; `real_volume` es cero en la mayor parte del histórico; la fuente es de un único broker; no hay todavía inferencia estadística, walk-forward, estrategia, backtest de cartera ni edge validado.

## 18. Ejemplo de experiencia con coste

`EXPERIENCE-V2-620ca0fd1edae2ce`, sesión `SESSION-GOLD-2015-01-02-COT`, LONG contrafactual, decisión 2015-01-02 13:00 UTC. Close 1182,57; spread 50 puntos = 0,50. A 5m: gross return -0,0000422808; tradable return -0,0004648922; coste de spread 0,0004226114; método `PROXY_COST`. Slippage: null / `UNAVAILABLE_NOT_ASSUMED_ZERO`. Hash: `cd738bd860c92b4dc25dd07f9bcc5795142887ed8ab3f9e7416015e9f0394bb8`.

## 19. Replay y memoria

Replay del ejemplo y de diez vecinos DEV recalculó hashes válidos. Dos iteraciones V2 crearon experimentos y episodios persistentes; la consolidación produjo `MEMORY-20260903T015047711266Z-87011fbc6b`, que referencia los diez `EXPERIENCE_ID` sin copiar los registros masivos a memoria. El estado final conserva `mode=RESEARCH_ONLY`, `live_trading=false` y `automatic_promotion_to_live=false`.

## 20. Recomendación para Prompt #4

Construir el protocolo de validación estadística antes de buscar parámetros: declarar métricas y nulos por adelantado; trabajar únicamente en DEV; usar bootstrap por sesiones, permutaciones, control de pruebas múltiples, sensibilidad al coste y estabilidad temporal; permitir una única evaluación de candidatos pre-registrados en VALIDATION; mantener LOCKED_OOS cerrado. El entregable debe ser un motor de evidencia y rechazo, no una estrategia ni un EA.
