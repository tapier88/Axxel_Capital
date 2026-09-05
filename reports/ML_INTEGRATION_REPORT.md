# AXXEL — integración ML y falsación XAUUSD 08:30

## 1. Código y arquitectura

Discovery Engine incorpora `run_ml_candidate`. La capa `src/ml` reutiliza el Experience Store, Evidence Registry, controles de leakage, walk-forward, bootstrap, Skeptic, Research Value, memoria y grafo. Tres adaptadores CPU entrenan clasificación direccional, probabilidades marginales de barreras ATR y regresiones MFE/MAE. El ensemble promedia probabilidades y mide desacuerdo. Se guardan 21 modelos nativos y calibradores, contrato causal, versiones, predicciones OOF y hashes.

## 2. Documentación

Actualizados README, AGENTS, misión, reglas del agente, arquitectura/flujo/value, schemas de features/outcomes, Experience Store, Discovery, hipótesis, Research Value, leakage, walk-forward, Skeptic, costes, promoción, OOS, validación, configuración, recursos, bucle operativo, conocimiento e índices. Dependencias reproducibles en `requirements-ml-lock.txt`.

## 3. Verificación

Suite completa final: 127 tests aprobados en 14,41 segundos. Incluye serialización/recarga de los tres boosters, contrato causal, separación temporal, configuración inmutable y abstención. Los 21 modelos nativos se recargaron y predijeron sobre entradas sintéticas. La instalación editable se verificó con `pip --dry-run`. Repeticiones con la misma configuración produjeron las mismas probabilidades y métricas. Evidencia: `reports/ML_VERIFICATION.json`.

Incidencia: la suite heredada abrió el LOCKED_OOS real mediante `allow_locked=True` antes de corregir ese bypass; sus checksums/replay también accedían a VALIDATION. El test inspeccionó la etiqueta de partición, no entrenó modelos con esos datos. No se puede afirmar que el holdout nunca se abrió durante esta tarea. El lector ahora deniega ese bypass, checksum y replay predeterminados son DEV-only y el test exige denegación. La incidencia permanece en `reports/ML_PARTITION_ACCESS_INCIDENT.json` y bloquea promoción pendiente de revisión.

## 4. Comparación direccional

1.282 sesiones válidas, 17 features y 1.027 predicciones OOF (2016–2019) dentro de DEV. Siete sesiones con horizonte incompleto excluidas. La hipótesis histórica de expansión excepcional a las 08:30 ya estaba rechazada; este experimento no la da por cierta.

| Modelo | Balanced accuracy | Log-loss | Brier multiclase |
|---|---:|---:|---:|
| XGBoost | 0,332543 | 1,110653 | 0,673431 |
| LightGBM | 0,333572 | 1,111166 | 0,673372 |
| CatBoost | 0,333572 | 1,110396 | 0,673158 |
| Ensemble | 0,332543 | 1,110466 | 0,673193 |
| Climatología de 2015 | 0,333333 | 1,085685 | 0,657947 |

Ensemble: error de calibración 0,046898; desviación media entre modelos 0,004984. MFE/MAE auxiliar: error absoluto medio aproximado de 5,00/5,08 puntos básicos. Las barreras marginales no representan orden de toques ni PnL de brackets y no alteraron la política primaria.

## 5. Economía

Cero operaciones con umbral congelado 0,50; PnL cero. No constituye rentabilidad positiva ni permite estimar expectativa por operación. Spread histórico proxy, slippage y costes completos no observados: no se presenta como resultado económico real.

## 6. Skeptic

Solo 2/7 gates ML pasan (calibración y desacuerdo); el Skeptic común pasa 3/8. No hay supervivencia económica. Permutar bloques, retrasar features siete sesiones y cambiar seeds +101/+202 deja la balanced accuracy alrededor de 1/3 y cero operaciones. No se seleccionó ninguna de esas variantes.

## 7. Veredicto

`REJECTED`. No hay evidencia de edge direccional monetizable para esta especificación. No se ajustaron umbrales, features, labels ni hiperparámetros según el resultado negativo. La configuración original permanece congelada.

## 8. Aprendizaje y siguiente experimento

El acuerdo entre boosters no crea información; calibración aceptable no implica discriminación. La siguiente investigación requiere nueva información causal, no más ajuste de esta familia: primero revisar la incidencia de acceso y completar costes observados; después pre-registrar el valor incremental de calendario/eventos conocido antes de la sesión, verificando explícitamente COT frente a la zona horaria del evento.

Reproducción:

```powershell
python scripts/run_ml_experiment.py --config config/ml_xauusd_0830_v1.json
```

Evidencia numérica canónica: `reports/evidence/ML_XAUUSD_0830_V1.json`. Las banderas de no inspección de ese reporte se refieren al runner ML; la incidencia de los tests está declarada separadamente.
