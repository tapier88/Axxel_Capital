# VALIDATION PROTOCOL

## Contrato vigente de datos

Toda nueva evidencia debe referenciar un dataset Data Engine elegible e inmutable. V1 no concede acceso a VALIDATION mediante flags; la ceremonia y capacidad independientes no se sustituyen por un certificado de calidad.

## Sistema integrado: Machine Learning

Discovery, entrenamiento, selección, calibración y ensemble ML son DEV-only. Un VALIDATION_READY necesita pre-registro y ceremonia independiente; la autorización ya consumida no se reutiliza. LOCKED_OOS permanece inaccesible. La primera evaluación ML no reclama validación confirmatoria ni rentabilidad real.

Protocolo de validation protocol.

## V0 implementada

La validación actual solo acepta un resultado si mantiene enlaces hypothesis → experiment → result, modo `RESEARCH_ONLY`, broker desconectado, cero órdenes y cero capital real. Siempre devuelve `edge_validated=false` y `promotion_allowed=false`. OOS, walk-forward, leakage y stress siguen siendo gates obligatorios pendientes para cualquier investigación de mercado futura.

## Evidence V1

`evaluate_hypothesis(H)` exige especificación congelada y produce un EVIDENCE_REPORT con efecto, incertidumbre, intervalos, p/FDR, bootstraps, estabilidad temporal/de régimen/coste/parámetros, muestra, calidad, controles negativos, skeptic, score y veredicto. Los estados alcanzables en discovery son REJECTED, DEV_SURVIVOR y, tras pre-registro, VALIDATION_READY. Nunca valida un edge ni autoriza trading.

## Ceremonia confirmatoria V1

`src/validation/confirmation.py` implementa una única autorización para confirmar cuatro especificaciones congeladas en `VALIDATION` 2020–2022. Antes de leer datos materializa en DEV los cuantiles declarados, verifica pre-registros/evidencia y congela manifiesto y protocolo con SHA-256. Holm es el control familiar principal y BH-FDR es complementario. Los gates predictivo y económico son independientes.

La ceremonia consumida produjo cuatro `VALIDATED_PREDICTIVE_RELATIONSHIP_NO_TRADE`: todos los efectos relativos replicaron, pero ningún retorno neto condicionado fue positivo. No existe `VALIDATED_ECONOMIC_CANDIDATE` ni autorización OOS.
