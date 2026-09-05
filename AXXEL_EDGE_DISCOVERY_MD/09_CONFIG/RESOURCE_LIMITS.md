# RESOURCE LIMITS

## Contrato vigente de datos

Dependencias locales Data Engine: `requirements-data-engine-lock.txt`, extra `.[data-engine]`. Pandera + Parquet + DuckDB; sin Great Expectations instalado, Spark ni GPU. Ejecución científica adicional conserva sus límites CPU existentes.

ML es CPU-only. Cada modelo recibe un número explícito de hilos y una cantidad acotada de iteraciones con early stopping. No se permiten GPU, TensorFlow, PyTorch, RL ni búsqueda exhaustiva en esta fase. Los modelos se ejecutan sobre la misma matriz con presupuesto controlado.
