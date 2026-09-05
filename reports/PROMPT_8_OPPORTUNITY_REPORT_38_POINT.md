# PROMPT #8 — COST REALITY + OPPORTUNITY DISCOVERY (38 PUNTOS)

Resultado: `REAL_TICK_DEV_UNAVAILABLE`; 18 `VOLATILITY_OPPORTUNITY_ONLY`; 0 `DIRECTION_SURVIVOR`; 0 `DEV_ECONOMIC_SURVIVOR`; decisión operativa `NO_TRADE`.

1. **Fuentes de coste nuevas:** cero fuentes nuevas utilizables. Se encontró una segunda instalación MT5 registrada cuya ruta ya no existe, y dos CSV locales OHLC sin bid/ask. Se localizaron HistData XAUUSD Generic ASCII y Dukascopy/JForex como candidatos autorizados, pero no se ingirió ninguno ni se mezcló con XM.

2. **Cobertura bid/ask:** 0% en DEV. XM M1 proxy cubre 100% de los costes computables. Slippage permanece `UNAVAILABLE_NOT_ASSUMED_ZERO`.

3. **Cost Reality Report:** estado `REAL_TICK_DEV_UNAVAILABLE`. XM proxy: spread points p50=37, p75=40, p90=43, p95=45; spread return p50=0.00030571, p75=0.00032737, p90=0.00035234, p95=0.00036720. Incluye distribución intradía, por régimen y cuartil de volatilidad, fuentes, hashes y procedencia.

4. **Hipótesis propuestas:** exactamente 30 `NEW_OPPORTUNITY_HYPOTHESES`.

5. **Distribución por familia:** diez familias con tres hipótesis cada una: VOLATILITY_EXPANSION, RANGE_BREAK, POST_COMPRESSION_EXPANSION, SESSION_TRANSITION, EXTREME_EXCURSION, MOMENTUM_BURST, BREAKOUT_CONTINUATION, FAILED_BREAKOUT, LIQUIDITY_SWEEP_PROXY y VOLATILITY_REGIME_TRANSITION.

6. **Edge-to-cost inicial:** medias expanding-train por hipótesis entre 2.73 y 12.99; 30/30 superaron 2 y 29/30 superaron 3. Estos valores solo asignan interés de investigación.

7. **Rechazadas por gross insuficiente:** 0/30. El problema de esta campaña no fue falta de excursión bruta; fue incapacidad direccional. Doce se rechazaron por no elevar robustamente la tasa de oportunidad frente al baseline.

8. **Opportunity Survivors:** 18: OPP-01, 02, 03, 11, 12, 13, 14, 16, 17, 18, 19, 21, 24, 25, 26, 27, 28 y 30. Estado final: `VOLATILITY_OPPORTUNITY_ONLY`.

9. **Distribución de excursiones:** entre survivors, p50 0.00126071–0.00301739; p75 0.00185449–0.00437524; p90 0.00266572–0.00633500; p95 0.00329906–0.00798601.

10. **Frecuencia:** 1.1663%–22.5038% del universo walk-forward; soporte 3.258–62.861 eventos y 278–1.031 sesiones.

11. **Mejor horizonte:** ninguno se promociona post-hoc. Descriptivamente, 60m tuvo el mayor Opportunity Value promedio; 30m produjo más survivors (11), seguido de 15m (4) y 60m (3). Cada horizonte permaneció congelado por hipótesis.

12. **Direction tests:** 36 pruebas predeclaradas LONG/SHORT sobre las 18 condiciones congeladas. Resultado: 36 `REJECTED`, 0 `DIRECTION_SURVIVOR`.

13. **Expected gross return direccional:** rango −0.00008012 a +0.00008012. El mejor lado fue OPP-03 SHORT: +0.00008012.

14. **Expected cost:** rango direccional 0.00026842–0.00033879. OPP-03 SHORT: 0.00027158.

15. **Expected net return:** todas las direcciones negativas, rango −0.00038276 a −0.00019145. Mejor IC95: OPP-03 SHORT [−0.00036480, −0.00001811].

16. **Break-even cost:** mejor dirección 0.00008012, muy inferior al coste esperado 0.00027158.

17. **Edge-to-cost final:** mejor dirección 0.2950; ninguna dirección se acercó a 1. La excursión absoluta era grande, pero su signo no era predecible.

18. **Walk-forward:** expanding train, test anual 2016–2019, purging y embargo iguales al horizonte. Ejemplo OPP-11: lift +0.01868, +0.01968, +0.01675 y +0.03253 en los cuatro años.

19. **Estabilidad temporal:** los 18 opportunity survivors superaron sus gates. La mejor dirección, OPP-03 SHORT, fue negativa en 2016, 2017, 2018 y 2019.

20. **Estabilidad por régimen:** OPP-11 mantuvo surplus positivo en RANGE, TREND_DOWN y TREND_UP. OPP-03 SHORT fue netamente negativo en los tres.

21. **Cost stress:** OPP-03 SHORT ya fue negativo a 0.75× (−0.00012356), y cayó a −0.00019145/−0.00025935/−0.00032724/−0.00046303 en 1×/1.25×/1.5×/2×.

22. **Skeptic:** los opportunity survivors soportaron remove-best-5%, top-10 sessions, winsorization, vecinos, concentración, gaps y controles aleatorios según sus registros. Las 36 direcciones fallaron; OPP-03 SHORT fue negativo en todos los ataques económicos.

23. **Multiple testing:** BH-FDR sobre las 30 oportunidades produjo 18 survivors. BH-FDR separado sobre 36 direcciones produjo cero survivors; el mejor neto tuvo q=1.0.

24. **DEV_ECONOMIC_SURVIVOR:** ninguno.

25. **NO_TRADE:** existen estados con movimientos grandes, pero no se encontró una dirección causal que pague el coste. `WAIT` sigue siendo la única decisión económica defendible.

26. **Nuevas memorias:** cierre formal de reversión y resultado de Opportunity V1 guardados en memoria semántica y long-term. Etiquetas: `REVERSAL_RELATIVE_VALIDATED_BUT_NOT_MONETIZABLE` y `DO_NOT_REOPEN_WITH_POSTHOC_FILTERS`.

27. **Knowledge Value:** 1.0.

28. **Research Value V3:** promedio 0.638853. La familia de reversión quedó en 0.01 salvo nueva evidencia externa.

29. **Opportunity Value:** 0.802470, máximo entre survivors. OPP-11: move 0.00151233, coste 0.00028536, ratio 5.30, frecuencia 11.44% y tasa de oportunidad 93.08%.

30. **Trade Value:** 0.0.

31. **Abstention Value:** +0.00028268 promedio sobre las 36 decisiones direccionales.

32. **VALIDATION:** cerrada; `validation_reads=0`, `validation_inspected=false`. No se reutilizó 2020–2022.

33. **LOCKED_OOS:** cerrado; `locked_oos_reads=0`, `locked_oos_inspected=false`. No se usó 2023–2024 ni siquiera para costes.

34. **Demo collector:** `PREPARED_NOT_EXECUTED`. Solo recopila prospectivamente bid, ask, spread, ticks, timestamps y movimiento de mid a 100/500/1000ms como proxy de slippage potencial; no contiene capacidad de enviar órdenes.

35. **Tests:** la suite cubre ratio edge/cost, labels, causalidad, K, survivors, dirección, walk-forward, purging, embargo, BH-FDR, procedencia, locks y enforcement no-trade del colector.

36. **Limitaciones:** costes XM proxy; sin ticks DEV; slippage desconocido; dirección contrafactual sin fills; 2015 solo calibración; la segunda fuente aún no está mapeada ni ingerida.

37. **Incertidumbre principal:** si una fuente independiente bid/ask confirma el coste XM y si alguno de los estados de alta excursión puede adquirir señal direccional con nueva información causal, sin cambiar su condición original.

38. **Recomendación exacta para Prompt #9:** ejecutar prospectivamente el colector demo/read-only durante una ventana predeclarada suficiente para estimar spread y slippage potencial; adquirir y mapear por separado HistData o Dukascopy XAUUSD sin fusionar brokers; congelar esa realidad de costes; no volver a reversión; conservar los 18 estados solo como detectores de volatilidad; abrir una nueva hipótesis direccional únicamente si aporta una variable causal nueva y pre-registrada. Mantener VALIDATION 2020–2022 y LOCKED_OOS cerrados.

Conclusión: **se encontró oportunidad de movimiento, no dirección monetizable**.
