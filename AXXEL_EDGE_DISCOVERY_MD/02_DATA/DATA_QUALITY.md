# DATA QUALITY

Data Engine valida esquema con Pandera y aplica reglas vectorizadas de mercado. `quality.json` y `findings.parquet` pertenecen a cada versión y se verifican mediante su manifiesto; los informes históricos no certifican nuevas ejecuciones.

Clasificaciones: FIX, KEEP_FLAGGED, REVIEW y REJECT. Solo se ordenan registros y se eliminan duplicados exactos en silver, nunca en RAW. Conflictos OHLC/timestamp, precios no finitos y valores imposibles rechazan el dataset. Gaps sin calendario comprobado exigen REVIEW; saltos, stale prices y spreads cero se conservan.

Estados: RESEARCH_GRADE (reservado), USABLE_WITH_LIMITATIONS, EXPLORATORY_ONLY y REJECTED. Los dos últimos no entran en Discovery, ML ni backtest. El score no anula los bloqueos. Fórmula, límites y detecciones: [Data Engine](DATA_ENGINE.md).

Piloto XAUUSD M1: 1.048.576 filas, 89,7073/100, EXPLORATORY_ONLY; 2.679 gaps REVIEW, 249 spreads cero, 146 alertas stale y un salto. No se eliminó ninguna vela. No se identifican automáticamente los gaps como cierres legítimos del broker.
