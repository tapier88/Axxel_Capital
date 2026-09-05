# STATE SCHEMA

## Contrato vigente de datos

Cada estado nuevo pertenece a gold registrado por Data Engine y conserva la versión de dataset y fuente. No construir estados de investigación leyendo directamente RAW.

Especificación de state schema.

## market-experience-v1

El estado se marca `FEATURES_AVAILABLE_AT_DECISION_TIME` e incluye symbol, SESSION_ID, UTC/COT, minuto de sesión, OHLC de la última barra completada, retornos 1h/3h/6h, rango, ATR causal, volatilidad causal, spread, volúmenes, distancias a extremos recientes, momentum, régimen transparente y calidad. `max_source_bar_index` permite probar el límite temporal.
