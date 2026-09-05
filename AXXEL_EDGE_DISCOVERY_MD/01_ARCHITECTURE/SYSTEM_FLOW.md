# SYSTEM FLOW

## Contrato vigente de datos

Flujo vigente: SOURCE → RAW inmutable → NORMALIZE → VALIDATE → CLEAN → QUALITY → FREEZE → dataset certificado → Discovery/candidato → ML/ensemble o prueba económica → costes/walk-forward → Skeptic → evidencia. EXPLORATORY_ONLY/REJECTED detienen el flujo antes de investigación.

1. Discovery recupera memoria, propone, deduplica y pre-registra un candidato.
2. La compuerta de partición autoriza únicamente DEV.
3. El contrato elimina todo campo futuro/coste de la matriz y verifica timestamps causales.
4. Un walk-forward expansivo separa cronológicamente fit, early stopping, calibración y test.
5. XGBoost, LightGBM y CatBoost reciben los mismos ejemplos; el ensemble promedia probabilidades y mide desacuerdo.
6. Las decisiones aplican umbrales congelados, costes y abstención `NO_TRADE`.
7. Skeptic intenta destruir calibración, estabilidad temporal y resultado económico.
8. Evidence Registry, reportes, modelos nativos, memoria y grafo conservan evidencia y falsaciones.
9. El resultado termina en `REJECTED`, `RESEARCH_ONLY` o `VALIDATION_READY`; nunca abre OOS ni ejecuta órdenes.
