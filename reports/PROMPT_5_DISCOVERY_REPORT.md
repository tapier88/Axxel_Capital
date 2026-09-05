# PROMPT #5 — INFORME DISCOVERY AUTÓNOMO V1

Fecha de cierre: 2026-09-03 UTC  
Campaña: `DISCOVERY-CAMPAIGN-DEV-V1`  
Modo: `RESEARCH_ONLY`  
Partición leída: `DEV` exclusivamente

## Resultado ejecutivo

Discovery Engine V1 completó de forma reproducible el ciclo memoria → generación → Research Value V2 → pre-registro → evidencia → Skeptic → persistencia → consolidación → grafo → siguiente prioridad. Probó 24 hipótesis acotadas, rechazó 20 y congeló cuatro como `VALIDATION_READY`. Las cuatro supervivientes expresan reversión relativa, pero sus retornos netos condicionados siguen siendo negativos; por eso se registraron como `NO_TRADE` y no como edges operables. No se abrió `VALIDATION`, no se tocó `LOCKED_OOS`, no se creó EA y no se enviaron órdenes.

## Entrega solicitada

1. **Hipótesis propuestas:** 24, con semilla `20260903` y firmas científicas deduplicadas.

2. **Hipótesis ejecutadas:** 24. El motor ejecutó una sola prueba por iteración y puede reanudarse sin repetir evidencia ya registrada.

3. **Distribución por familia:** dos hipótesis en cada familia: `TEMPORAL`, `VOLATILITY`, `RANGE`, `MOMENTUM`, `REVERSAL`, `CONTINUATION`, `BREAKOUT`, `MEAN_REVERSION`, `REGIME`, `COST`, `CROSS_FEATURE` y `DATA_QUALITY`.

4. **Ranking inicial por Research Value V2:**

| Puestos | Score | Hipótesis |
|---:|---:|---|
| 1–12 | 0.724468 | DISC-07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 19, 20 |
| 13–16 | 0.704533 | DISC-01, 02, 03, 04 |
| 17–22 | 0.684599 | DISC-05, 06, 17, 18, 23, 24 |
| 23 | 0.680633 | DISC-22 |
| 24 | 0.642970 | DISC-21 |

El orden completo e inmutable está en `reports/evidence/PROMPT_5_DISCOVERY_CAMPAIGN.json`.

5. **Hipótesis rechazadas:** 20: DISC-01 a 08, 11 a 14 y 17 a 24. Las únicas no rechazadas fueron DISC-09, 10, 15 y 16.

6. **Motivos principales de rechazo:** control negativo fallido 12; FDR/múltiples pruebas 10; dirección incorrecta 9; inestabilidad temporal 9; inestabilidad de parámetros 9; materialidad económica insuficiente 4. Una hipótesis puede tener varios motivos.

7. **Diagnóstico de persistencia de volatilidad:** `CONFIRMED_REJECTION`. Efecto original 0.00006972; el máximo cociente desplazado/original fue 0.97268, y al controlar volatilidad lenta quedó 0.00003098. Los shifts de 1/5/10/20/60 sesiones conservaron gran parte del efecto; el stationary bootstrap fue estable, pero precisamente esa persistencia bajo desplazamientos apoya estructura lenta/confusión y no causalidad utilizable.

8. **Anomalías estadísticas:** el escaneo simétrico evaluó 18 ventanas de 15 minutos con FDR desde el inicio. Diecisiete fueron distintas de la media de sesión; solo minutos 105–119 no fueron significativos (`q=0.065934`). El mayor exceso fue minutos 135–149 (+0.00010247) y el mayor defecto minutos 0–14 (-0.00011059). Esto describe estructura de volatilidad, no dirección ni entrada.

9. **Señales predictivas:** cuatro relaciones de reversión relativa: subida extrema → SHORT, bajada extrema → LONG, cercanía al máximo → SHORT y cercanía al mínimo → LONG. Son `PREDICTIVE_SIGNAL` relativa, no `TRADABLE_EDGE`.

10. **Candidatos `DEV_SURVIVOR`:** 0 al cierre. Los cuatro que superaron todos los gates fueron congelados inmediatamente en el siguiente estado permitido, `VALIDATION_READY`.

11. **Candidatos `VALIDATION_READY`:** DISC-09 `UP_MOVE_REVERSES`, DISC-10 `DOWN_MOVE_REVERSES`, DISC-15 `NEAR_HIGH_REVERTS` y DISC-16 `NEAR_LOW_REVERTS`. Sus especificaciones quedaron pre-registradas; no fueron ejecutadas fuera de DEV.

12. **Mejores effect sizes relativos:**

| Hipótesis | Efecto | bps | IC95 | Media neta condicionada |
|---|---:|---:|---:|---:|
| DISC-16 | 0.00027954 | 2.7954 | [0.00023518, 0.00032748] | -0.00004298 |
| DISC-15 | 0.00023624 | 2.3624 | [0.00018736, 0.00028161] | -0.00006845 |
| DISC-10 | 0.00016597 | 1.6597 | [0.00014015, 0.00019434] | -0.00014863 |
| DISC-09 | 0.00014619 | 1.4619 | [0.00012039, 0.00017221] | -0.00015453 |

Todos tienen `q=0.00257014`, pero la última columna es negativa: la mejora contra el base no basta para operar.

13. **Estabilidad temporal:** las cuatro candidatas `VALIDATION_READY` alcanzaron proporción favorable 1.0 en los cortes DEV evaluados y cubrieron entre 1.277 y 1.282 sesiones. Nueve rechazadas fallaron este gate.

14. **Robustez a costes:** las cuatro candidatas conservaron el efecto relativo hasta 2x costes. Esto no corrige su rentabilidad neta absoluta negativa. El coste histórico sigue siendo mayoritariamente `PROXY_COST`.

15. **Controles negativos:** las cuatro candidatas pasaron los controles. Doce hipótesis fueron rechazadas por fallarlos; el diagnóstico de volatilidad mostró el caso clave donde significancia y bootstrap no implican causalidad.

16. **Conocimiento consolidado:** se crearon 12 memorias semánticas por familia y cuatro memorias `NO_TRADE`, siempre con enlaces a evidencia fuente. El almacén queda en 6 memorias working, 6 episódicas, 48 semánticas y 0 long-term. Los rechazos también reducen prioridad futura de búsquedas redundantes.

17. **Contradicciones abiertas:** (a) significancia cruda frente a supervivencia bajo outcomes temporalmente desplazados; (b) mejora relativa de reversión frente a retorno neto absoluto negativo; (c) evidencia de un solo broker frente a generalización; (d) costes proxy frente a ejecución tick-by-tick no observada.

18. **Hypothesis graph:** `hypotheses/graph.json` contiene 61 nodos y 81 aristas: 24 `PARENT`, 24 `CHILD`, 21 `FALSIFIES`, 4 `REFINES`, 4 `SUPPORTS`, 2 `REPLACES` y 2 `CONTRADICTS`.

19. **Cambio de Research Value:** el ranking inicial agrupaba ideas direccionales nuevas en 0.724468. Tras incorporar falsaciones, saturación y redundancia, las cuatro candidatas quedaron primeras en 0.387651–0.387663; los rechazos bajaron hasta 0.153827–0.270641. El score se usa para elegir investigación, nunca trades.

20. **`VALIDATION` cerrado:** confirmado por artefacto (`validation_inspected=false`) y por pruebas de bloqueo. Solo se escribieron pre-registros para uso futuro.

21. **`LOCKED_OOS` cerrado:** confirmado (`locked_oos_inspected=false`) y protegido por el mismo guard de particiones.

22. **Pruebas ejecutadas:** 55 pruebas unitarias/integración pasan. Cubren generación, deduplicación, reproducibilidad, diversidad, Research Value y penalizaciones, soporte mínimo, grafo y relaciones, aislamiento DEV, locks VALIDATION/OOS, consolidación, diagnóstico de volatilidad, escaneo intradía y pipeline Evidence/Skeptic completo.

23. **Limitaciones:** un solo broker/símbolo; ticks bid/ask parciales; slippage no observado; costes proxy en gran parte del histórico; cuantiles derivados dentro de DEV; controles causales y stationary bootstrap todavía V1; no hay evaluación confirmatoria; la memoria long-term no debe promoverse hasta evidencia independiente; y no existe prueba de tradabilidad.

24. **Incertidumbre de mayor valor:** si las cuatro relaciones de reversión relativa, congeladas sin retoques, generalizan a datos independientes y si alguna conserva retorno neto absoluto positivo bajo costes reales. La primera parte requiere una ceremonia controlada en `VALIDATION`; la segunda necesita mejores ticks/costes o datos de otro broker. Ninguna justifica abrir `LOCKED_OOS`.

25. **Recomendación para Prompt #6:** ejecutar una única ceremonia confirmatoria en `VALIDATION` para las cuatro especificaciones inmutables, tratándolas como una familia FDR común, sin cambiar umbrales, dirección, horizonte ni costes después de ver resultados. Exigir efecto relativo, retorno neto absoluto positivo, estabilidad temporal, sensibilidad a costes y Skeptic. Rechazar y consolidar si fallan; si alguna sobrevive, congelarla como candidata OOS, pero mantener `LOCKED_OOS`, MQL5 y trading real cerrados.

## Componentes implementados

- Generación y deduplicación: `src/research/hypothesis_generator.py`.
- Orquestación reanudable: `src/research/discovery_engine.py`.
- Grafo persistente: `src/research/hypothesis_graph.py`.
- Diagnósticos: `src/research/volatility_diagnostic.py`, `intraday_structure.py`.
- Research Value V2: `src/value/research_value.py`.
- Evidencia/soporte/condiciones: `src/validation/evidence_engine.py`.
- Stationary bootstrap: `src/validation/bootstrap.py`.
- Registro científico inmutable: `src/research/evidence_registry.py`.
- Límites: `config/discovery_limits_v1.json`.
- Ejecución: `scripts/run_discovery_campaign.py`.
- Pruebas: `tests/research/test_discovery_engine.py`.

## Regla de cierre

El resultado de esta campaña es conocimiento reutilizable, no autorización para operar. `NO_LIVE_TRADING`, `NO_REAL_ORDERS` y `NO_AUTOMATIC_PROMOTION_TO_LIVE` siguen vigentes.
