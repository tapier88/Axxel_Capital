# PROMPT #6 — INFORME DE CEREMONIA CONFIRMATORIA

Fecha: 2026-09-03 UTC  
Ceremonia: `VALIDATION-CEREMONY-REVERSAL-RELATIVE-V1`  
Modo: `RESEARCH_ONLY`  
Resultado: 4 relaciones predictivas relativas validadas, 4 `NO_TRADE`, 0 candidatos económicos

## Resumen ejecutivo

Las cuatro hipótesis congeladas replicaron en `VALIDATION` 2020–2022 con la dirección esperada, IC95 positivo, Holm significativo, bootstrap estable, cobertura temporal y controles Skeptic. Ninguna produjo retorno neto condicionado positivo con el cost model congelado. La conclusión confirmatoria es: existe una relación relativa reproducible de reversión extrema, pero no una estrategia rentable. No se autoriza `LOCKED_OOS`, EA, órdenes ni promoción.

## Entrega solicitada

1. **Hashes originales:**

| Hipótesis | `spec_hash` original |
|---|---|
| DISC-09 | `ab18da50363cf9c0d93b7cdb84ac903319da0b732bd304f3180efc831b76d2af` |
| DISC-10 | `506d3b139884ae86a53c8acc0be0adbdad169b60defa17bd67a735108414cc66` |
| DISC-15 | `0c3a315cd83ad1d126dcabcc674f6700cd5e64bc4188dca29206422771e2f0b0` |
| DISC-16 | `4ee63ad0496902a6b913333d8bfe61c00dd25088ccb6644a79417a298abac7ab` |

2. **Integridad:** confirmada antes de leer `VALIDATION`. Se comprobó igualdad campo por campo contra la fuente determinista, enlace de pre-registro, `spec_hash`, hash del archivo DEV y `spec_hash` dentro de la evidencia. Los tres primeros hashes usan el formato histórico de creación; el manifiesto conserva además un hash normalizado de la fotografía científica actual. La diferencia de formato quedó explicada y no representa mutación.

3. **Manifest:** `reports/validation/VALIDATION_CEREMONY_MANIFEST.json`, hash `f343ce96e5b8001c8f7097b57f17de8963ba4f23dac98b82a2aa28b300c77843`. Protocolo inmutable: hash `200002797d1fad69361ba7404fdeee6edc8b8a9001cdc92e4e7717199e044916`.

4. **Sesiones utilizadas:** 775 sesiones únicas de `VALIDATION`; se cargaron 629.985 experiencias LONG/SHORT/WAIT en una única lectura autorizada.

5. **Observaciones condicionadas:** DISC-09 45.122; DISC-10 43.729; DISC-15 18.385; DISC-16 15.253. Las sesiones pareadas fueron 772, 772, 765 y 768, respectivamente.

6–9. **Efectos DEV, VALIDATION, replication ratio e IC95:**

| ID | DEV | VALIDATION | bps | Ratio | IC95 VALIDATION |
|---|---:|---:|---:|---:|---:|
| DISC-09 | 0.00014619 | 0.00013301 | 1.3301 | 0.9099 | [0.00009464, 0.00017078] |
| DISC-10 | 0.00016597 | 0.00018827 | 1.8827 | 1.1344 | [0.00014722, 0.00022819] |
| DISC-15 | 0.00023624 | 0.00040381 | 4.0381 | 1.7093 | [0.00032957, 0.00047572] |
| DISC-16 | 0.00027954 | 0.00045131 | 4.5131 | 1.6145 | [0.00037361, 0.00053299] |

10. **Bootstrap:** las cuatro tuvieron `sign_stability=1.0` y proporción favorable 1.0 en 2.000 remuestras por sesión. Moving-block y stationary bootstrap también mantuvieron IC95 positivo. Sus IC95 stationary fueron: DISC-09 [0.00009642, 0.00017178], DISC-10 [0.00014924, 0.00022737], DISC-15 [0.00033018, 0.00047849], DISC-16 [0.00035644, 0.00055101].

11. **Permutation p:** 0.00024994 para cada hipótesis, limitado por 4.000 permutaciones.

12. **Holm adjusted p:** 0.00099975 para cada hipótesis. Las cuatro pasan el control familiar confirmatorio.

13. **BH-FDR:** `q=0.00024994` para cada hipótesis; se reporta solo como complemento.

14. **Estabilidad temporal:** signo positivo en 9/9 cortes predefinidos (2020, 2021, 2022 y sus semestres) para las cuatro. Concentración anual: 0.3791, 0.4121, 0.4113 y 0.4496; todas bajo el límite 0.60. No se seleccionaron periodos favorables retrospectivamente.

15. **Estabilidad por régimen:** DISC-15 y DISC-16 fueron positivos en todos los regímenes con soporte evaluable. DISC-09 fue positivo en RANGE y TREND_UP, sin comparación pareada disponible en TREND_DOWN. DISC-10 fue positivo en TREND_DOWN, negativo en RANGE (-0.00051601) y sin comparación pareada en TREND_UP. Esta heterogeneidad queda como contradicción, no como subgrupo explotable.

16. **Skeptic:** 8/8 ataques superados por cada candidato: winsorization, eliminación del mejor/peor 5%, concentración temporal, dependencia de outliers, calidad, gaps y coste 2x. El control de estructura lenta adicional también pasó; efectos shift-7: -0.00000207, -0.00000199, -0.00002327 y +0.00004621.

17–19. **Retorno bruto, neto y MFE/MAE:**

| ID | Gross | Spread cost | Net | MFE | MAE | Hit rate | Payoff |
|---|---:|---:|---:|---:|---:|---:|---:|
| DISC-09 | -0.00001136 | 0.00019620 | -0.00020756 | 0.00119574 | -0.00121589 | 44.48% | 0.8738 |
| DISC-10 | 0.00000863 | 0.00019423 | -0.00018561 | 0.00127565 | -0.00138301 | 47.13% | 0.8375 |
| DISC-15 | 0.00001155 | 0.00017923 | -0.00016768 | 0.00125744 | -0.00121715 | 45.57% | 0.9037 |
| DISC-16 | 0.00007624 | 0.00017827 | -0.00010203 | 0.00132006 | -0.00134546 | 49.32% | 0.8742 |

20. **Sensibilidad del retorno neto absoluto a costes:**

| ID | 1.0x | 1.25x | 1.5x | 2.0x |
|---|---:|---:|---:|---:|
| DISC-09 | -0.00020756 | -0.00025661 | -0.00030566 | -0.00040376 |
| DISC-10 | -0.00018561 | -0.00023416 | -0.00028272 | -0.00037984 |
| DISC-15 | -0.00016768 | -0.00021249 | -0.00025730 | -0.00034692 |
| DISC-16 | -0.00010203 | -0.00014660 | -0.00019117 | -0.00028030 |

El efecto relativo sobrevivió a 2x, pero el retorno absoluto empeoró. En esta partición todas las observaciones condicionadas usan `PROXY_COST`; no hubo `REAL_TICK_COST` suficiente y la confianza económica es `LOW`.

21. **`VALIDATION_FAILED`:** ninguno.

22. **`VALIDATED_PREDICTIVE_RELATIONSHIP_NO_TRADE`:** DISC-09, DISC-10, DISC-15 y DISC-16.

23. **`VALIDATED_ECONOMIC_CANDIDATE`:** ninguno. No se generó `OOS_CANDIDATE_MANIFEST`.

24. **Nuevas memorias semánticas:** 6: cuatro resultados individuales, una consolidación de replicación familiar y una conclusión explícita `NO_TRADE`. Total semantic: 54.

25. **Nuevas memorias long-term:** 2, ambas enlazadas a evidencia DEV y VALIDATION. La más precisa conserva: relación relativa reproducible de reversión extrema, retorno neto negativo, `NO_TRADE`.

26. **Contradicciones:** efecto relativo positivo frente a retorno absoluto negativo; DISC-10 no replica dentro de RANGE; ausencia de algunos pares en regímenes; solidez estadística frente a costes proxy y slippage desconocido; mayor efecto VALIDATION que DEV en DISC-15/16 sin que ello cree valor económico.

27. **Valores separados:** `knowledge_value=1.0`, `research_value=0.2`, `trade_value=0.0`. Son heurísticas distintas: el conocimiento aumentó, repetir la misma pregunta perdió prioridad y la utilidad operable permanece nula.

28. **Sin optimización en VALIDATION:** confirmado. No se cambiaron cuantiles, umbrales, horizonte, dirección, target, feature, coste, régimen o subgrupo. Los cuatro umbrales numéricos fueron materializados desde DEV antes de hashear el protocolo.

29. **LOCKED_OOS:** jamás leído. Estado persistente: `locked_oos_reads=0`; artefacto: `locked_oos_inspected=false`. El hard lock continúa activo.

30. **Pruebas:** se añadieron 14 pruebas confirmatorias que cubren los 16 controles solicitados. La batería completa terminó con **69/69 pruebas aprobadas** en 30,015 segundos.

31. **Limitaciones:** un broker; costes proxy en todo el subconjunto condicionado VALIDATION; slippage ausente; resolución mínima de p determinada por 4.000 permutaciones; regímenes sin pares en algunos candidatos; contrafactuales, no ejecuciones; la relación mide diferencia contra el complemento de sesión, no rentabilidad autónoma; los tres hashes históricos iniciales usan una serialización previa aunque su contenido fue verificado campo por campo.

32. **Recomendación exacta para Prompt #7:** no abrir OOS. Volver a DEV con una campaña económica pequeña y pre-registrada que pregunte si una política causal `ENTER vs WAIT` puede convertir la relación validada en retorno neto positivo mediante disponibilidad y coste observables antes de entrar. Primero enriquecer el cost model con bid/ask histórico real o una segunda fuente/broker; luego probar pocas reglas simples de abstención, con umbrales definidos en DEV, penalización de complejidad y `expected_net_return > 0` como métrica primaria. Cualquier candidato debe recorrer nuevamente DEV → nueva ceremonia VALIDATION; el `VALIDATION` ya consumido por estas cuatro especificaciones no puede reutilizarse.

## Controles operativos

- Estado de autorización: `state/validation_ceremony_state.json` (`CONSUMED`, una autorización, una lectura).
- Resultado hash: `5697dcb882a6da87834bd7e5419224d9cb3706401089255d629d964dd1438fa4`.
- Órdenes enviadas: 0.
- Capital real: 0.
- EA creado: no.
- Promoción live: no.
