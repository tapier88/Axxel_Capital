# BOOTSTRAP

Protocolo de bootstrap.

## V1 implementada

El remuestreo nunca opera sobre filas M1 independientes. `session_bootstrap` remuestrea efectos de sesión, de forma pareada cuando condición y base conviven en la misma sesión. `block_bootstrap` remuestrea bloques cronológicos de sesiones. Ambos son deterministas por semilla y reportan distribución, mediana, intervalos 90/95%, estabilidad de signo y proporción favorable.
