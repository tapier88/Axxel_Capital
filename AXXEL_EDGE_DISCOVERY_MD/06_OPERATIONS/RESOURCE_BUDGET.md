# RESOURCE BUDGET

## Contrato vigente de datos

Data Engine usa CPU, Parquet Zstandard, rowgroups de 100.000 filas y DuckDB con dos hilos/1 GB para consultas. La ingesta materializa únicamente un extracto acotado; no promete procesamiento out-of-core de toda la historia. No se añade infraestructura distribuida.

Procedimiento operativo para resource budget.
