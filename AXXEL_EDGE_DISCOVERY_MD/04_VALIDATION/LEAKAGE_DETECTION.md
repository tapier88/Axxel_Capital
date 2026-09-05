# LEAKAGE DETECTION

## Contrato vigente de datos

Data Engine comprueba aislamiento antes de leer payloads y antes de derivar features/labels. No se mezclan particiones para normalización, limpieza, umbrales o warmup. Las pruebas adversariales usan archivos sintéticos; no se inspeccionan holdouts reales ni sus hashes.

ML falla cerrado si la matriz contiene prefijos `label_`, `outcome_` o `cost_`, si una fuente alcanza el timestamp de decisión, si cambia el orden/hash de features o si aparece una partición distinta de DEV. Imputación, early stopping y calibración se ajustan solo con historia anterior al test.

`DevOnlyMLData` no acepta nombres de partición ni `allow_locked`. Los tests verifican esa ausencia de escape. Todo fold purga el horizonte y aplica embargo; se prohíben shuffle, K-fold aleatorio y selección sobre las métricas OOF finales.
