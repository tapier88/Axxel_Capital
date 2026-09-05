# RESEARCH VALUE

## Sistema integrado: Machine Learning

La evidencia ML utiliza Research Value V2 existente. Las probabilidades calibradas, desacuerdo y errores OOF se reportan por separado; no son reward económico. No se incrementa prioridad solo por añadir complejidad ni se reoptimiza un rechazo.

Define research value y su evaluación.

## Heurística V0

Media ponderada de incertidumbre, information value y reproducibilidad, penalizada por coste normalizado. Los pesos viven en `config/runtime_policy.json`; la salida está acotada a `[0,1]`.

## V1 implementada

La prioridad combina `expected_information_gain`, `uncertainty_reduction`, `novelty`, `cost`, `relevance` y `previous_evidence`. Aplica descuento creciente a preguntas ya resueltas, por lo que evidencia fuerte —positiva o negativa— reduce la prioridad de repetir el experimento. El score ordena investigación; no representa valor de trading.
