# WALK FORWARD

## Contrato vigente de datos

Las particiones se aíslan antes de features y labels mediante Data Engine. Walk-forward/purga/embargo siguen operando dentro de DEV certificado; no se emplea validación aleatoria ni normalización global de la historia.

Se usa ventana expansiva anual dentro de DEV. Para cada año de test, la historia anterior se divide cronológicamente 70% fit, 15% early stopping y 15% calibración. Entre train y test se purga el horizonte completo y se aplica embargo. Las predicciones concatenadas de 2016–2019 forman la única evaluación OOF; ningún hiperparámetro cambia después de observarla.
