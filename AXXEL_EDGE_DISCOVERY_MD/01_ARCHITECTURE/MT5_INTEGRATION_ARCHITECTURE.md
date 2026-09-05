# MT5 INTEGRATION ARCHITECTURE

## Contrato vigente de datos

Data Engine V1 admite OHLCV Parquet acotado. Los antiguos comandos MT5/MCP de historia mixta y publicación de ticks están deshabilitados antes de conectar. Un adaptador posterior deberá preservar la respuesta original antes de normalizar y demostrar aislamiento temporal; no se inventa retrospectivamente un RAW original.

Separación entre investigación Python y ejecución MT5/MQL5.

## Estado V0

Los MCP `terminal`, `metaeditor` y `marketdata` tienen configuración local, pero el loop no los importa ni invoca. Su uso futuro debe limitarse primero a adquisición de datos y compilación/pruebas demo, siempre después de validación. La promoción a live no existe en V0.
