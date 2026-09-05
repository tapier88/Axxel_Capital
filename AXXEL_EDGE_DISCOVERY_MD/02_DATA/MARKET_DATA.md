# MARKET DATA

Especificación de market data.

## Dataset XAUUSD V1

El raw inmutable está en `data/raw/xauusd/xauusd_1h_c079cd1a82ab.json`. Su URL canónica es `https://www.metatrader.com/en/symbols/xauusd`. El query solicitó todo el rango 2000–2026 y el servidor devolvió únicamente 110 barras recientes; esa es la cobertura disponible, no una selección del pipeline.

## Dataset GOLD/XAUUSD V2

La fuente principal es el terminal XM Global: símbolo exacto `GOLD`, alias internacional XAUUSD. El M1 canónico cubre 2015-01-02 a 2024-12-31 con 3.532.606 barras. Una fuente separada contiene 56.013 ticks bid/ask de una sesión de 2024. Los manifests en `data/raw/gold_m1/` y `data/raw/gold_ticks/` registran broker, servidor, columnas, cobertura, método, transformaciones y hashes.
