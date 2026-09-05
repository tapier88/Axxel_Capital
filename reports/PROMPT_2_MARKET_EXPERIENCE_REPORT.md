# Prompt #2 — Motor de experiencia real del mercado

Fecha de ejecución: 2026-09-02 COT / 2026-09-03 UTC. Modo: `RESEARCH_ONLY`.

## 1–3. Datos, calidad y cobertura

- Instrumento: XAUUSD (Gold vs US Dollar), URL canónica: https://www.metatrader.com/en/symbols/xauusd
- Fuente: MetaTrader MarketData MCP público y read-only.
- Cobertura devuelta al solicitar 2000–2026: 110 barras H1, `2026-08-27T01:00:00Z` a `2026-09-02T22:00:00Z`.
- Fuente: time, open, high, low, close, volume. Normalizado: symbol, timestamp_open_utc, OHLC, tick_volume, real_volume=null, spread=null.
- Calidad: 0 duplicados, 0 timestamps desordenados, 0 NaNs obligatorios, 0 OHLC inválidos y 0 volúmenes negativos.
- Gaps: tres cierres diarios de 180 minutos y un cierre de fin de semana de 3060 minutos; se conservan, no se rellenan.
- El terminal local no reconoce XAUUSD. No existen ticks, bid/ask, spread ni real volume para este símbolo.

Raw: `data/raw/xauusd/xauusd_1h_c079cd1a82ab.json`. Hash del archivo: `f710961309cff1803bf27f1aabadaf67dfde0fd9d81f19f7431abec858d3e7ab`. Hash de barras normalizadas: `cfcbc493cdf286ab701127c9fa7580d7d72ee7f51ad43e2e7e0b5a68274a720e`.

## 4–7. Schemas y costes

El contrato completo está en `config/market_experience_schema_v1.json`.

- STATE: únicamente features disponibles al cierre de la barra que precede la decisión. Incluye UTC/COT, OHLC completado, retornos 1h/3h/6h, rango, ATR causal, volatilidad causal, actividad, distancias, momentum, régimen y calidad.
- ACTION: WAIT, LONG o SHORT, siempre contrafactual y nunca ejecución real.
- OUTCOME: información futura separada. H1 permite future_return/MFE/MAE/excursiones/volatilidad a 60m. Los horizontes 5m/15m/30m son null.
- COST: WAIT=0 exacto. LONG/SHORT no tienen coste calculable porque no existe spread; `tradable_return_60m=null` y `outcome_status=GROSS_ONLY_UNPRICED`.

La decisión se timestampa al cierre de la barra usada como estado. Así se corrigió preventivamente el leakage que habría ocurrido usando el OHLC completo en el timestamp de apertura.

## 8–10. Sesiones, experiencias y particiones

- 5 sesiones COT, ventana 08:00–12:30, con contexto previo conservado.
- 75 experiencias: cinco estados por sesión × tres acciones. Las cinco sesiones y sus referencias de contexto/ventana están persistidas en `data/sessions/dataset-11d5cf82a841e95415fb3bc0.json`.
- DEV: 27, 28 y 31 de agosto (45 experiencias).
- VALIDATION: 1 de septiembre (15 experiencias).
- LOCKED_OOS: 2 de septiembre (15 experiencias).

La partición está congelada en `data/partitions/dataset-11d5cf82a841e95415fb3bc0.json`. El retrieval de discovery solo consulta DEV por defecto.

## 11–12. Pruebas y leakage

Pasan 20 pruebas: estado, IDs, hipótesis, experimentos, episodios, memoria, value, UTC/COT, sesiones, duplicados, gaps, límites state/outcome, horizontes, costes, contrafactuales, partición bloqueada, hashes, reconstrucción byte a byte, retrieval/replay e integración del loop de mercado.

No se detectó leakage en los registros construidos. Las pruebas exigen `max_source_bar_index < source_future_bar_index` y rechazan cualquier campo `future_*` dentro del estado.

## 13–14. Limitaciones y esqueletos

- Cobertura de solo cinco sesiones y granularidad H1: insuficiente para descubrir o validar edge.
- Sin costes reales, los retornos LONG/SHORT no son operables.
- Régimen V0 y distancia normalizada son heurísticos, no modelos calibrados.
- JSON es suficiente para 75 filas; Parquet deberá evaluarse al adquirir cientos de miles.
- Permanecen pendientes M1/ticks XAUUSD, walk-forward/OOS estadístico, bootstrap, permutation, stress, replay masivo, scheduling, EA, riesgo y ejecución.
- EURUSD/USDJPY no se expandieron porque XAUUSD conserva limitaciones estructurales.

## 15. Ejemplo completo

El registro completo y verificable está en `reports/examples/dataset-11d5cf82a841e95415fb3bc0_experience.json`.

Resumen: `EXPERIENCE-a7b202c3aec1c5729a17642f`, sesión `SESSION-XAUUSD-2026-08-27-COT`, decisión `2026-08-27T13:00:00Z` / `08:00 COT`, acción contrafactual LONG, gross 60m `0.0021374332461476797`, tradable return null por ausencia de spread.

## 16–17. Retrieval, replay y memoria

El loop recuperó diez vecinos DEV mediante distancia normalizada. Replay recalculó los diez hashes correctamente; no accedió a LOCKED_OOS. Dos iteraciones de mercado generaron dos episodios y una memoria semántica con referencias a los diez EXPERIENCE_ID.

Estado final: iteración 4; working 4, episodic 4, semantic 2, long-term 0. La ausencia de long-term es correcta porque todavía no existe evidencia suficiente.

## 18. Recomendación para Prompt #3

Adquirir XAUUSD M1 o ticks con bid/ask desde un broker/fuente autorizada, versionar un dataset sustancial, verificar calendario y gaps, migrar el store a Parquet si el volumen lo requiere y recalcular costes/horizontes. Solo después implementar el protocolo estadístico OOS/walk-forward sobre hipótesis predefinidas, sin tocar live ni optimizar beneficios.
