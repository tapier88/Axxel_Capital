# PROMPT #7 — INFORME ECONÓMICO DEV (38 PUNTOS)

Campaña: `ECONOMIC-DISCOVERY-V1`. Modo: `RESEARCH_ONLY`. Resultado: **24/24 políticas REJECTED; cero DEV_ECONOMIC_SURVIVOR; WAIT es óptimo**.

1. **Nuevos datos de coste:** se consultó read-only el terminal XM Global para una hora de 2015, 2016, 2017, 2018 y 2019. No devolvió ticks en ninguno de los cinco años. No se incorporó ninguna fuente nueva.

2. **Cobertura tick/bid-ask:** `REAL_TICK_COST=0%` en DEV; `PROXY_COST=100%` de los costes computables. La muestra tick existente es de 2024 y no se leyó porque pertenece a `LOCKED_OOS`.

3. **Cost Model V2:** conserva `SOURCE_ID`, broker, timestamp, `REAL_TICK_COST`, `PROXY_COST` y confidence; prioriza tick real y cae explícitamente a spread M1. Fuente `MT5-XMGLOBAL-GOLD-M1-V1`, broker `XM Global Limited`, confianza `MEDIUM_PROXY_ONLY`. Slippage: `UNAVAILABLE_NOT_ASSUMED_ZERO`.

4. **Políticas propuestas:** 24 `NEW_ECONOMIC_HYPOTHESES`, pre-registradas como 4 señales congeladas × 6 filtros.

5. **Políticas ejecutadas:** 24/24, solo en DEV.

6. **Condiciones usadas:** low spread, alta magnitud de señal, volatilidad intercuartil, cost/ATR bajo, minuto 60–210 y régimen RANGE. Cada política añade una sola condición.

7. **Ranking por Research Value (top 5):** DISC-09+HIGH_SIGNAL_MAGNITUDE 0.361503; DISC-16+HIGH_SIGNAL_MAGNITUDE 0.360861; DISC-15+HIGH_SIGNAL_MAGNITUDE 0.360811; DISC-09+SELECTED_TIME_WINDOW 0.360515; DISC-09+LOW_COST 0.360322. Todas `REJECTED`. Ranking completo en el artefacto JSON.

8. **Ranking por Trade Value:** todas empatan en 0.0 al no superar el gate. Orden informativo por neto: la menos negativa fue `NEW-ECO-DISC-15-LOW_COST_ATR-V1` con −0.00016235.

9. **Entry rate:** rango 0.0632%–73.3808%; promedio entre políticas 42.6545%. En la mejor política por neto: 28.1685% (8.519 entradas de 30.243 señales elegibles).

10. **WAIT rate:** rango 26.6192%–99.9368%; promedio 57.3455%. Mejor política: 71.8315% (21.724 abstenciones).

11. **Expected gross return:** rango −0.00058914 a +0.00008934. Mejor política: +0.00008934.

12. **Expected costs:** rango 0.00022717–0.00028716. Mejor política: 0.00025168, 2.82× su gross esperado.

13. **Expected net return:** las 24 son negativas, rango −0.00086359 a −0.00016235. Mejor IC95 clusterizado por sesión: [−0.00024452, −0.00008018].

14. **Break-even cost:** mejor política 0.00008934; muy por debajo de sus costes históricos p50 0.00023711, p75 0.00029573, p90 0.00032603 y p95 0.00033953.

15. **MFE/MAE:** mejor política MFE +0.00121695 y MAE −0.00115743. Entre políticas: MFE 0.00067506–0.00208504; MAE −0.00263660 a −0.00068912.

16. **Hit rate:** mejor política 45.6626%; rango total 28.00%–55.56%.

17. **Payoff:** mejor política 0.8850; rango total 0.5135–1.0867.

18. **Walk-forward:** expanding-window con 2015 como calibración; test 2016/2017/2018/2019. La mejor política produjo −0.00010163, −0.00006851, −0.00025215 y −0.00012066 respectivamente. Purging y embargo: 30 minutos para su horizonte de 30 minutos.

19. **Estabilidad temporal:** 0/24 superó el gate. La mejor política fue negativa en los cuatro años; solo 2016-H2 y 2017-H2 fueron positivos, sin compensar el resto.

20. **Estabilidad por régimen:** mejor política: RANGE −0.00011829, TREND_DOWN −0.00129262, TREND_UP −0.00016351. No existe régimen positivo.

21. **Cost stress:** 0/24 fue positivo incluso a 0.75×. Mejor política: 0.75× −0.00009943; 1× −0.00016235; 1.25× −0.00022527; 1.5× −0.00028819; 2× −0.00041403.

22. **Multiple testing:** familia de 24 comparaciones, BH-FDR. Para la mejor política `q=1.0`; ninguna pasa significancia económica positiva.

23. **Skeptic failures:** 24/24 fallaron. La mejor falló remove-best-5%, remove-best-10-sessions, winsorization, 1.5× costes, spread +10%, vecinos de señal débil/fuerte, dependencia de régimen y sensibilidad a gaps.

24. **Políticas REJECTED:** 24/24. Dos además fallaron soporte mínimo; todas fallaron neto, IC95, estabilidad y Skeptic.

25. **DEV_ECONOMIC_SURVIVOR:** ninguno.

26. **ENTER vs WAIT:** `value_enter<0` para las 24; `value_wait=0`. Para la menos negativa, `ABSTENTION_VALUE=+0.00016235`, por lo que WAIT domina.

27. **Knowledge learned:** low cost/ATR reduce la pérdida más que los demás filtros probados, pero no la vuelve positiva. Filtrar más no resuelve una relación gross demasiado pequeña frente al spread.

28. **Memoria consolidada:** registro completo en `hypotheses/economic_registry_v1.json`; memoria semántica `MEMORY-20260903T165550481866Z-196459d1d7`, promovida a long-term.

29. **Knowledge Value:** 1.0: la familia económica queda resuelta negativamente bajo el coste proxy y evita rescates post-hoc.

30. **Research Value:** promedio 0.321687. El ranking refleja información/precisión, no aptitud para operar.

31. **Trade Value:** 0.0.

32. **Abstention Value:** promedio +0.00027649; positivo significa que WAIT evita pérdida esperada.

33. **VALIDATION:** no se reabrió; `validation_reads=0`, `validation_inspected=false`.

34. **LOCKED_OOS:** permaneció cerrado; `locked_oos_reads=0`, `locked_oos_inspected=false`. La muestra de ticks 2024 tampoco fue inspeccionada durante la campaña.

35. **Pruebas:** 89/89 aprobadas en la suite completa; 17 son específicas de Prompt #7. Cubren causalidad, procedencia, Trade/Abstention Value, purging, embargo, walk-forward temporal, locks, soporte, complejidad, estrés y campaña acotada.

36. **Limitaciones:** un broker; costes proxy; slippage desconocido; 2015 solo calibración interna; outcomes contrafactuales sin fills; algunos gaps de horizonte; no existe evidencia tick DEV.

37. **Incertidumbre de mayor valor:** coste bid/ask y slippage independientes para 2015–2019. Como los resultados ya son negativos sin añadir slippage, esta incertidumbre no rescata candidatos; puede hacerlos peores.

38. **Recomendación exacta para Prompt #8:** adquirir una fuente independiente y autorizada de bid/ask histórico DEV (otro broker) o iniciar forward/demo para estimar spread y slippage reales; congelar Cost Model V2 antes de cualquier nueva campaña; no retocar ni ampliar estas 24 políticas; si se autoriza otra familia, pre-registrarla pequeña y evaluarla con walk-forward DEV. No reutilizar 2020–2022 oportunísticamente y mantener `LOCKED_OOS` cerrado.

Conclusión operativa: **NO_TRADE**. La señal relativa validada no produjo ningún estado causal pre-entry donde ENTER supere a WAIT después de costes.
