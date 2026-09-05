# PROMPT #4 — Motor de evidencia estadística y rechazo

Fecha: 2026-09-03 UTC. Alcance: exclusivamente DEV 2015–2019. No se inspeccionó VALIDATION ni LOCKED_OOS, no se generaron señales ni se ejecutaron órdenes.

## 1. Módulos implementados

- Registro y congelación: `src/research/evidence_registry.py`.
- Orquestador `evaluate_hypothesis(H)`: `src/validation/evidence_engine.py`.
- Bootstrap de sesiones/bloques, permutación, FDR, stress de costes, estabilidad, barrera OOS y Skeptic: `src/validation/`.
- Research value V1: `src/value/research_value.py`.

## 2. Pruebas

Pasan 41/41 pruebas. Las nuevas cubren reproducibilidad de bootstrap/permutación, FDR, base rates, splits, costes, vecinos, controles negativos, registro inmutable, hash de pre-registro, aislamiento DEV, bloqueo VALIDATION/OOS, score, skeptic y memoria.

## 3. Hipótesis de calibración

Se congelaron cuatro: hash arbitrario de sesiones; ventana 08:00–08:30; persistencia de volatilidad causal; y expansión a las 08:30. La batería final contiene 12 comparaciones predeclaradas. El registro global contabiliza 28 ejecuciones al incluir una corrida parcial fallida y las repeticiones de desarrollo posteriores; todas quedaron preservadas, no borradas. No hubo búsqueda masiva.

## 4. Controles negativos

El control absurdo produjo efecto LONG 30m de 0,02065 bps, p=0,47988, FDR=0,95976 e IC95 [-1,0865; 1,0539] bps: correctamente rechazado. La persistencia de volatilidad parecía fuerte, pero el outcome desplazado siete sesiones retuvo 0,00006342 frente al efecto original 0,00006972; superó el máximo permitido del 50% y falsó el candidato. Los cuatro casos fallaron al menos un control negativo.

## 5. Bootstrap

- Control absurdo: efecto 0,0000020647; IC95 [-0,00010865, 0,00010539]; favorable 51,1%.
- Ventana temprana: -0,00011660; IC95 [-0,00012145, -0,00011152]; favorable en dirección declarada 0%.
- Persistencia: 0,00006972; IC95 [0,00006487, 0,00007461]; favorable 100%, pero falsada después.
- 08:30: -0,00009922; IC95 [-0,00010372, -0,00009478]; favorable 0%.

Los moving-block bootstraps de 20 sesiones confirmaron signos similares; esto no anuló los demás gates.

## 6. Permutación

Se ejecutaron 4.000 permutaciones deterministas por hipótesis. P nominal: 0,47988; 1,0; 0,00024994; 1,0. Las pruebas pareadas usan sign-flips por sesión y la no pareada permuta agregados de sesión.

## 7. Multiple testing

Se aplicó penalización por comparaciones previstas y BH-FDR global. P ajustados: 0,95976; 1,0; 0,00299925; 1,0. El resultado significativo fue rechazado por control negativo. Para confirmación posterior se recomienda Holm además de FDR.

## 8. Estabilidad temporal

Se evaluaron cinco años y diez semestres. Proporción favorable: control 53,33%; ventana temprana 0%; persistencia 100%; 08:30 0%. También se midieron RANGE, TREND_UP y TREND_DOWN. La persistencia fue positiva en los tres, pero no superó la falsación desplazada.

## 9. Estabilidad ante costes

Solo el control LONG tenía target tradable. Se recalculó con 1x, 1,25x, 1,5x y 2x coste; el signo permaneció positivo, pero el efecto fue económicamente insignificante y ruido estadístico. Para targets de volatilidad el stress se marcó no aplicable, sin inventar significado económico.

## 10. Estabilidad de parámetros

Ventana temprana: límites 25/30/35 minutos, todos contrarios a la dirección. Persistencia: cuantiles 0,70/0,75/0,80, todos positivos. 08:30: vecinos 08:20, 08:25, 08:35 y 08:40, todos contrarios a la afirmación. No se eligió retrospectivamente un vecino mejor.

## 11. Falsaciones

Skeptic ejecutó winsorization 5%, retirada del mejor/peor 5%, concentración temporal, coste 2x cuando aplicaba, dependencia de outliers, calidad y gaps. También se aplicaron outcomes desplazados, condición aleatoria determinista y permutación de sesiones. Los horizontes que cruzan gaps se excluyen, no se imputan.

## 12–14. Veredictos

- REJECTED: 4.
- DEV_SURVIVOR: 0.
- VALIDATION_READY actual: 0.

Ventana temprana y 08:30 fallaron dirección, FDR, tiempo y vecinos. El control falló materialidad, FDR, tiempo y controles. Persistencia superó bootstrap/FDR/tiempo/parámetros, pero falló el control desplazado. Un pre-registro preliminar se conserva como historia; el registro vigente fue revocado a REJECTED y no autoriza VALIDATION.

## 15–16. Aislamiento

El resumen registra `validation_inspected=false` y `locked_oos_inspected=false`. `PartitionGuard` permitió solo DEV. Dos intentos deliberados contra VALIDATION y LOCKED_OOS fallaron y quedaron registrados antes de cualquier lectura.

## 17. Memoria

Estado: working 6, episodic 6, semantic 8, long-term 0. La memoria conserva los cuatro informes, motivos de rechazo y la contradicción histórica DEV_SURVIVOR → REJECTED de volatilidad.

## 18. Research value

V1 añade ganancia esperada, reducción de incertidumbre, novedad, coste, relevancia y evidencia previa. La persistencia falsada recibió prioridad 0,231181, menor que preguntas menos resueltas. Es prioridad de investigación, nunca trade value.

## 19. Limitaciones

Los gates son V1 y cubren cuatro condiciones declarativas. Faltan odds ratios/eventos, medianas inferenciales, stationary bootstrap, HAC, calendario macro, múltiples brokers y calibración formal del umbral de control negativo. El resultado desplazado puede reflejar persistencia lenta genuina o confusión; no se decide cuál sin hipótesis nueva. Los ticks siguen parciales.

## 20. Recomendación para Prompt #5

No abrir VALIDATION. Diagnosticar la falsación de volatilidad solo en DEV mediante purging/embargo, desplazamientos múltiples predeclarados, detrending por año/mes/régimen, controles de volatilidad lenta, bootstrap estacionario y comparación entre horizontes. Debe producir una nueva hipótesis causal congelada o confirmar el rechazo. Solo si elimina la explicación de estructura lenta podrá crear un nuevo `VALIDATION_READY`; no debe crear EA ni tocar LOCKED_OOS.

Artefacto de máquina: `reports/evidence/PROMPT_4_CALIBRATION_BATTERY.json`.
