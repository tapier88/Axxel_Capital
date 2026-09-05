# AUTONOMOUS LOOP

## Contrato vigente de datos

Antes de retrieval/ML/backtest, exigir certificado Data Engine elegible. Los comandos históricos descritos abajo no permiten releer datasets sin certificar; la iteración V1 JSON está retirada. Piloto: `python scripts/run_data_engine.py --config config/data_engine_xauusd_m1_v1.json`. Su EXPLORATORY_ONLY detiene la parte científica; no bajar gates para continuar.

## Sistema integrado: Machine Learning

`python scripts/run_ml_experiment.py --config config/ml_xauusd_0830_v1.json` entra por Discovery Engine, ejecuta CPU-only, persiste evidencia, Research Value, memoria, grafo y modelos nativos. Termina antes de VALIDATION/OOS. No opera. Cambiar símbolo requiere manifiesto DEV y una nueva configuración pre-registrada.

Procedimiento operativo para autonomous loop.

## Ciclo
1. Leer estado.
2. Recuperar memoria relevante.
3. Medir incertidumbre.
4. Generar hipótesis.
5. Calcular valor de investigación.
6. Ejecutar experimento.
7. Atacar con Skeptic Engine.
8. Validar.
9. Guardar experiencia.
10. Consolidar memoria.
11. Actualizar valor.
12. Seleccionar siguiente experimento.

## Implementación V0

`python scripts/run_autonomous_loop.py` ejecuta exactamente una iteración persistente. El paso de validación actual comprueba seguridad y trazabilidad del flujo, no robustez de mercado. No selecciona órdenes, no usa MCP y no promueve estrategias. Repetir el comando reutiliza la hipótesis activa y permite que episodios suficientes se consoliden.

`python scripts/run_market_experience_iteration.py --symbol XAUUSD` añade retrieval/replay de experiencias reales DEV. Dos iteraciones dejaron dos episodios y una memoria semántica con referencias a diez EXPERIENCE_ID. El análisis no calcula rentabilidad agregada ni inspecciona LOCKED_OOS.

`python scripts/run_market_v2_iteration.py` ejecuta el equivalente sobre GOLD M1 V2. El ciclo verifica hashes de archivos y registros, consulta solo DEV, guarda hipótesis/experimento/episodio, consolida referencias y actualiza value V0. Sigue siendo un dry-run: `broker_connected=false`, cero órdenes y ninguna promoción.

## Discovery V1

`python scripts/run_discovery_campaign.py` ejecuta o reanuda una campaña acotada. Cada iteración selecciona y prueba una sola hipótesis; después persiste evidencia, memoria, grafo y prioridades. La semilla y los límites están congelados en configuración. El flujo falla antes de leer `VALIDATION` o `LOCKED_OOS`; tampoco importa un cliente de trading, compila un EA ni envía órdenes.
