# PROMPT #6 — ENTREGA EXACTA DE 40 PUNTOS

Esta revisión amplía el informe original sin sustituirlo y sin releer `VALIDATION`. Todos los valores proceden del resultado sellado `5697dcb882a6da87834bd7e5419224d9cb3706401089255d629d964dd1438fa4`.

1. **Integridad de las cuatro especificaciones:** PASS. Coinciden campo por campo con el catálogo determinista, pre-registros y evidencia DEV; los thresholds numéricos fueron resueltos en DEV antes del protocolo.

2. **Hashes originales:** DISC-09 `ab18da50363cf9c0d93b7cdb84ac903319da0b732bd304f3180efc831b76d2af`; DISC-10 `506d3b139884ae86a53c8acc0be0adbdad169b60defa17bd67a735108414cc66`; DISC-15 `0c3a315cd83ad1d126dcabcc674f6700cd5e64bc4188dca29206422771e2f0b0`; DISC-16 `4ee63ad0496902a6b913333d8bfe61c00dd25088ccb6644a79417a298abac7ab`.

3. **Hash del ceremony manifest:** `f343ce96e5b8001c8f7097b57f17de8963ba4f23dac98b82a2aa28b300c77843`. Protocolo: `200002797d1fad69361ba7404fdeee6edc8b8a9001cdc92e4e7717199e044916`.

4. **Sesiones VALIDATION:** 775 sesiones únicas, 2020-01-01 a 2022-12-31.

5. **Observaciones por candidato:** DISC-09 45.122; DISC-10 43.729; DISC-15 18.385; DISC-16 15.253.

6. **DEV effect:** DISC-09 0.00014619; DISC-10 0.00016597; DISC-15 0.00023624; DISC-16 0.00027954.

7. **VALIDATION effect:** DISC-09 0.00013301; DISC-10 0.00018827; DISC-15 0.00040381; DISC-16 0.00045131.

8. **Replication ratio:** DISC-09 0.9099; DISC-10 1.1344; DISC-15 1.7093; DISC-16 1.6145.

9. **IC95:** DISC-09 [0.00009464, 0.00017078]; DISC-10 [0.00014722, 0.00022819]; DISC-15 [0.00032957, 0.00047572]; DISC-16 [0.00037361, 0.00053299].

10. **Bootstrap:** 2.000 session, 2.000 moving-block y 2.000 stationary por candidato. Los cuatro tuvieron `sign_stability=1.0`, proporción favorable 1.0 e IC95 positivo bajo los tres métodos.

11. **Permutation p:** 0.00024994 para cada candidato, resolución limitada por 4.000 permutaciones.

12. **Holm-adjusted p:** 0.00099975 para los cuatro; Holm fue el control familiar principal.

13. **BH-FDR q:** 0.00024994 para los cuatro; métrica complementaria, no criterio principal.

14. **Temporal stability:** signo positivo en 9/9 periodos predefinidos para cada candidato. `year_concentration`: 0.3791, 0.4121, 0.4113 y 0.4496; todas bajo 0.60.

15. **Regime stability:** DISC-15/16 positivos en RANGE, TREND_UP y TREND_DOWN. DISC-09 positivo en RANGE/TREND_UP y sin par evaluable TREND_DOWN. DISC-10 positivo en TREND_DOWN, negativo en RANGE y sin par evaluable TREND_UP.

16. **Skeptic verdict:** SUPPORT para las cuatro: 8/8 ataques estándar y control slow-structure superados. No modificó ninguna especificación.

17. **Gross return:** DISC-09 -0.00001136; DISC-10 +0.00000863; DISC-15 +0.00001155; DISC-16 +0.00007624.

18. **Net/tradable return:** DISC-09 -0.00020756; DISC-10 -0.00018561; DISC-15 -0.00016768; DISC-16 -0.00010203.

19. **MFE:** DISC-09 0.00119574; DISC-10 0.00127565; DISC-15 0.00125744; DISC-16 0.00132006.

20. **MAE:** DISC-09 -0.00121589; DISC-10 -0.00138301; DISC-15 -0.00121715; DISC-16 -0.00134546.

21. **Hit rate:** DISC-09 44.48%; DISC-10 47.13%; DISC-15 45.57%; DISC-16 49.32%.

22. **Payoff ratio:** DISC-09 0.8738; DISC-10 0.8375; DISC-15 0.9037; DISC-16 0.8742. Average win/loss derivados de los agregados sellados: DISC-09 +0.00108967/-0.00124700; DISC-10 +0.00115981/-0.00138490; DISC-15 +0.00114392/-0.00126578; DISC-16 +0.00117947/-0.00134922.

23. **Expected value:** coincide con el retorno neto medio: -0.00020756, -0.00018561, -0.00016768 y -0.00010203. Todos fallan `expected_net_return > 0`.

24. **Costes 1x/1.25x/1.5x/2x:** DISC-09 -0.00020756/-0.00025661/-0.00030566/-0.00040376; DISC-10 -0.00018561/-0.00023416/-0.00028272/-0.00037984; DISC-15 -0.00016768/-0.00021249/-0.00025730/-0.00034692; DISC-16 -0.00010203/-0.00014660/-0.00019117/-0.00028030. Todo el subconjunto condicionado usa `PROXY_COST`; `REAL_TICK_COST` no está disponible y slippage permanece `UNAVAILABLE_NOT_ASSUMED_ZERO`.

25. **VALIDATION_FAILED:** ninguno.

26. **VALIDATED_PREDICTIVE_RELATIONSHIP_NO_TRADE:** DISC-09, DISC-10, DISC-15 y DISC-16.

27. **VALIDATED_ECONOMIC_CANDIDATE:** ninguno.

28. **Nuevas memorias semánticas:** 6; cuatro individuales, una familiar y una conclusión explícita `RELATIVE_REVERSAL_REPLICATES_BUT_IS_NOT_DIRECTLY_MONETIZABLE`. Total: 54.

29. **Nuevas memorias long-term:** 2, con referencias completas a DEV, VALIDATION y las cuatro hipótesis. La conclusión precisa es relación relativa replicada + retorno neto negativo + `NO_TRADE`.

30. **Contradicciones abiertas:** predictividad relativa frente a utilidad absoluta negativa; DISC-10 negativo en RANGE; regímenes sin pares; costes exclusivamente proxy; slippage desconocido; DISC-15/16 más fuertes en VALIDATION pero todavía no monetizables.

31. **Knowledge value:** 1.0, alto por replicación independiente y conclusión reutilizable.

32. **Research value:** 0.2, bajo para repetir estas mismas cuatro preguntas ya resueltas.

33. **Trade value:** 0.0, porque ninguna condición tiene expected net return positivo.

34. **Ausencia de reoptimización:** confirmada. No cambiaron threshold, quantile, ventana, horizonte, dirección, feature, régimen, coste, condición ni target después del protocolo.

35. **VALIDATION no usado para discovery:** confirmado. `discovery_on_validation=false`; no se generaron hipótesis ni se buscaron subgrupos.

36. **LOCKED_OOS cerrado:** confirmado. `locked_oos_reads=0`, `locked_oos_inspected=false` y no existe `OOS_CANDIDATE_MANIFEST`.

37. **Pruebas ejecutadas:** 72/72 aprobadas. Incluyen integridad, hashes, autorización única, no-discovery, no-mutación, Holm, BH-FDR, ratios, gates, estabilidad, costes, Skeptic, cuarentena, hard lock, long-term, separación de valores y persistencia.

38. **Limitaciones:** un broker; costes proxy; slippage ausente; p limitado por 4.000 permutaciones; algunos regímenes sin pares; contrafactuales y no ejecuciones; el efecto es relativo al complemento de sesión; tres hashes originales usan la serialización histórica, aunque el contenido se verificó campo por campo.

39. **Decisión:** volver a DEV. No preparar candidato OOS porque hay cero candidatos económicos.

40. **Prompt #7 recomendado:** construir en DEV un `ECONOMIC_DISCOVERY_V1` pequeño y pre-registrado para comparar causalmente `ENTER vs WAIT`, priorizando coste observable, frecuencia y expected net return. Antes, enriquecer bid/ask histórico real o incorporar una segunda fuente/broker. Probar pocas reglas simples de abstención, sin usar resultados de VALIDATION para escogerlas. Toda nueva especificación deberá recorrer DEV y una nueva validación independiente; `LOCKED_OOS` seguirá cerrado.
