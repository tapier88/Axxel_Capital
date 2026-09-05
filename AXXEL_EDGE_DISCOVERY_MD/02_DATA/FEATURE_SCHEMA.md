# FEATURE SCHEMA

## Contrato vigente de datos

Las features proceden de silver certificado y de ventanas pasadas contiguas. No se usan ventanas de N filas como si fueran N minutos atravesando gaps. La receta incluye hashes del código de derivación; un cambio crea otro dataset.

Las features ML deben comenzar por `state_`, existir antes de `decision_timestamp_utc` y figurar en un orden congelado con hash. Para 08:30 V1 se usan retornos 1/5/15/30/60, rango, ATR14 causal, volatilidad 15/60 causal, distancias a extremos, momentum, spread, tick volume y one-hot del régimen. `state_minute_of_session` se excluye por ser constante.

Quedan prohibidos `label_*`, `outcome_*`, `cost_*`, timestamps futuros, identificadores y cualquier normalización calculada fuera del train de cada fold. La mediana se aprende en train; las categorías tienen vocabulario congelado. El mismo tensor se entrega a los tres boosters.
