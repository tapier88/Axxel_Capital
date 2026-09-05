# HYPOTHESIS ENGINE

## Contrato vigente de datos

Un nuevo pre-registro debe identificar dataset/certificado Data Engine y receta. No reutilizar una hipótesis congelada sustituyendo silenciosamente el dataset, features o política de calidad.

## Sistema integrado: Machine Learning

Antes de entrenar se fijan instante, población, horizonte, features, label ATR, folds, seeds, hiperparámetros, calibración, ensemble, abstención, costes y gates. Evidence Registry conserva la configuración completa y rechaza modificaciones al mismo experimento. El nodo ML refina la pregunta de mercado sin borrar la hipótesis histórica rechazada.

Reglas y responsabilidades del componente hypothesis engine.

## V0

Crea una hipótesis `ACTIVE` con pregunta, declaración, racional, condición de falsación, tags e incertidumbres. Nunca rellena datos de mercado ausentes ni declara edge.

## Generador V1

`src/research/hypothesis_generator.py` produce condiciones observables y outcomes cuantificables en 12 familias: `TEMPORAL`, `VOLATILITY`, `RANGE`, `MOMENTUM`, `REVERSAL`, `CONTINUATION`, `BREAKOUT`, `MEAN_REVERSION`, `REGIME`, `COST`, `CROSS_FEATURE` y `DATA_QUALITY`. Consulta registro y memoria, deduplica la firma científica y etiqueta cada propuesta como `NOVEL`, `REFINEMENT` o `RETEST_WITH_NEW_EVIDENCE`.

`src/research/hypothesis_graph.py` persiste nodos y relaciones `PARENT`, `CHILD`, `REFINES`, `CONTRADICTS`, `SUPPORTS`, `REPLACES` y `FALSIFIES` en `hypotheses/graph.json`. El grafo conserva tanto resultados favorables como falsaciones.
