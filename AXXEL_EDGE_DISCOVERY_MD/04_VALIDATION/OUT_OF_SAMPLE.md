# OUT OF SAMPLE

## Contrato vigente de datos

V1 solo expone DEV. Los certificados no son una autorización VALIDATION/OOS. La ceremonia independiente de VALIDATION necesitará su capacidad explícita; LOCKED_OOS permanece inaccesible. El piloto lee únicamente un rowgroup DEV íntegro de la fuente legacy y preserva la incidencia histórica anterior.

## Hard lock e incidencia ML

ParquetExperienceStore rechaza ahora LOCKED_OOS incluso con `allow_locked=True`; checksum y replay predeterminados solo leen DEV. Una prueba heredada ejecutada durante la integración ML sí abrió antes el archivo real con el bypass. No entrenó ni seleccionó modelos con sus outcomes, pero el hecho no se borra: ver `reports/ML_PARTITION_ACCESS_INCIDENT.json`. Cualquier afirmación futura de holdout nunca abierto requiere revisar esta incidencia.

Protocolo de out of sample.

## Barrera V1

`PartitionGuard` autoriza solo DEV durante DISCOVERY y registra accesos permitidos y denegados. VALIDATION requiere fase propia y pre-registro inmutable. LOCKED_OOS no está autorizado en discovery ni validation. La batería Prompt #4 leyó solo DEV; pruebas explícitas de acceso a VALIDATION/OOS fallaron antes de abrir archivos.

Prompt #6 consumió `VALIDATION` una sola vez para las cuatro especificaciones pre-registradas. El estado auditable registra una autorización, una carga del dataset y cero lecturas `LOCKED_OOS`. Como no surgió ningún candidato económico, no se generó `OOS_CANDIDATE_MANIFEST` y 2023–2024 continúa bajo hard lock.
