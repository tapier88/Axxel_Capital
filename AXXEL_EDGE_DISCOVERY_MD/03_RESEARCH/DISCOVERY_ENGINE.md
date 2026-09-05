# DISCOVERY ENGINE

## Contrato vigente de datos

Discovery exige gold Data Engine elegible a través de ParquetExperienceStore antes de leer payloads. El score de calidad no es Research Value. El piloto EXPLORATORY_ONLY no autoriza una nueva campaña.

## Sistema integrado: Machine Learning

`DiscoveryEngine.run_ml_candidate()` envía un candidato congelado a los tres boosters, calibración y ensemble dentro del mismo registro científico. Los resultados vuelven a Evidence Registry, Research Value, Semantic Memory y grafo. Los estados ML son REJECTED, RESEARCH_ONLY y VALIDATION_READY. El runner es `python scripts/run_ml_experiment.py --config config/ml_xauusd_0830_v1.json`.

## V1 operativa

`src/research/discovery_engine.py` coordina una campaña reproducible y reanudable usando exclusivamente `DEV`. El flujo es: recuperar memoria y registro de evidencia, generar un catálogo pequeño, deduplicar, calcular Research Value V2, seleccionar una hipótesis, pre-registrarla, ejecutar Evidence/Skeptic, persistir el resultado, actualizar memoria y grafo, y recalcular prioridades.

Los límites de `config/discovery_limits_v1.json` fijan 24 propuestas, 24 iteraciones, una prueba por iteración, hasta cuatro perturbaciones, 1.000 bootstrap, 2.000 permutaciones, profundidad causal máxima dos y soportes mínimos de 5.000 filas, 200 sesiones y tres años. No se permite búsqueda exhaustiva.

Los estados son `PROPOSED`, `TESTING`, `REJECTED`, `DEV_SURVIVOR` y `VALIDATION_READY`. Un resultado solo alcanza `VALIDATION_READY` después de base rate, efecto, bootstrap, permutación, FDR, estabilidad temporal, costes, vecindad de parámetros, controles negativos y Skeptic. Esa etiqueta crea un pre-registro inmutable y detiene el flujo antes de leer `VALIDATION`.

La campaña V1 ejecutó 24 hipótesis, rechazó 20 y congeló cuatro como `VALIDATION_READY`. Las cuatro tienen retorno neto absoluto condicionado negativo y se registraron además como `NO_TRADE`: no son `TRADABLE_EDGE`.
