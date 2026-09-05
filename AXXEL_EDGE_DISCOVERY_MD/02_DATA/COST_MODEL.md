# COST MODEL

## Contrato vigente de datos

El certificado del dataset aporta la procedencia de spread/point y sus limitaciones. V1 no certifica ticks históricos ni slippage ejecutado; siguen siendo costes proxy/no disponibles, nunca cero implícito. Los CSV externos sin certificar no se abren ni para calcular hashes.

## Sistema integrado: Machine Learning

ML etiqueta con retornos netos disponibles y evalúa decisiones OOF como gross menos spread, sin descontarlo dos veces. Slippage y comisiones no observadas no se presentan como cero real. PROXY_COST permite falsación, pero impide VALIDATION_READY. El coste 2x es un estrés de spread, no una estimación de slippage.

Especificación de cost model.

## V0 implementada

WAIT tiene coste exacto cero. Para LONG/SHORT se usa bid/ask o spread de barra cuando exista. En el dataset actual no existe ninguno: el coste y `tradable_return_60m` son null y el resultado queda `GROSS_ONLY_UNPRICED`. El sistema no convierte gross return en retorno operable.

## V2 implementada

GOLD M1 incluye spread de broker en puntos. LONG entra aproximadamente a `ask = bid_close + spread` y sale a bid; SHORT entra a bid y sale aproximadamente a ask futura. Esto se etiqueta `PROXY_COST`. En la muestra temporal cubierta por ticks, entrada/salida usan bid/ask observado y se etiquetan `REAL_TICK_COST`. WAIT conserva coste cero. Slippage no observado permanece `null` con estado `UNAVAILABLE_NOT_ASSUMED_ZERO`; nunca se inventa cero.
