# MULTIPLE TESTING CONTROL

## Sistema integrado: Machine Learning

El experimento ML congela cuatro comparaciones (tres boosters y ensemble), sin búsqueda de parámetros. El ensemble es el endpoint principal; no se selecciona el mejor booster después de ver resultados. Un p nominal aislado no autoriza promoción.

Protocolo de multiple testing control.

## V1 implementada

Cada hipótesis declara comparaciones previstas. El p nominal recibe primero una penalización por esa familia y luego Benjamini-Hochberg controla FDR en el registro global. Un p menor a 0,05 no basta para sobrevivir. Holm o Bonferroni se reservan para familias confirmatorias pequeñas donde cualquier falso positivo sea inaceptable.

La función `holm_bonferroni` está implementada. La ceremonia `REVERSAL_RELATIVE_V1` trató las cuatro especificaciones como una sola familia: Holm fue decisivo y BH-FDR meramente informativo.
