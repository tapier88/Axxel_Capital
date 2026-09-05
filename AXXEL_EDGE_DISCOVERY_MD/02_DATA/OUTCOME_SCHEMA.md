# OUTCOME SCHEMA

## Contrato vigente de datos

Los outcomes se derivan dentro de la partición ya certificada. El futuro no disponible se mantiene nulo; no se cruzan fronteras ni se rellenan labels con otro dataset. Gold M1 reutiliza los horizontes actuales.

Además del label terminal direccional, dos clasificadores binarios por booster estiman si la excursión LONG/SHORT supera 0,25 ATR más spread proxy. Ambas barreras pueden alcanzarse en una misma sesión: son probabilidades marginales auxiliares y no modifican la política primaria. No se infiere orden de toques ni PnL de brackets.

## Sistema integrado: Machine Learning

ML usa DOWN/NO_TRADE/UP. En 08:30 V1, UP/DOWN exige retorno de esa dirección neto de spread superior a 0,25 ATR causal a 30 minutos; el resto es NO_TRADE. Cuatro regresiones auxiliares estiman MFE/MAE de LONG/SHORT en los mismos folds. Son barreras terminales, no primera barrera tocada: los extremos agregados no identifican el orden intrabar. Ningún outcome entra en features.

Especificación de outcome schema.

## market-experience-v1

El outcome se marca `FUTURE INFORMATION — LABEL ONLY`. Incluye retorno futuro, MFE, MAE, excursiones y volatilidad realizada. Con H1 solo se calcula 60m; 5m/15m/30m son null con motivo explícito. Gross y tradable return son campos distintos.
