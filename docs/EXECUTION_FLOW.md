# Flujos de ejecución

## A. Data flow

SOURCE → RAW → HASH → NORMALIZE → QUALITY → CERTIFICATE → FROZEN DATASET.

Data Engine conserva originales antes de transformar. La normalización no corrige
precios/gaps/spreads silenciosamente. QUALITY puede bloquear; CERTIFICATE exige evidencia
por campo, intervalo, instrumento, uso y entorno. Un score no concede permiso.
Antes de cualquier lectura, incluso hash/cache, se verifica autorización del consumer.

## B. Research flow

DISCOVERY → PREREGISTRATION → DEV → WALK-FORWARD → SKEPTIC → REJECT / VALIDATION_READY.

Es el contrato del flujo; requiere datos certificados. Features causales, purga/embargo,
costes acreditados, falsaciones preservadas y parámetros congelados. VALIDATION_READY
no abre VALIDATION: ceremonia humana independiente. LOCKED_OOS permanece cerrado.

## C. Architecture change flow

OBSERVE → DOCUMENT → PROPOSE → SHADOW → SANDBOX → CHALLENGER → VALIDATE → PROMOTE / REJECT.

Cambios mínimos aditivos, evidencia y rollback. La aprobación de diseño no habilita
producción. Tras cambios aprobados del master, regenerar/verificar ZIP automáticamente
como parte del cierre del agente, sin borrar versiones anteriores.

## D. Track B

XM DEMO → FORWARD CAPTURE → RAW → UTC → CONTRACT → INCIDENTS → G4 REVIEW.

Representación lógica: UTC debe observarse antes y después de cada request; no se agrega
retroactivamente al final. T0 propio durable verificado y lock preceden la primera petición.
V1 está revocada; V2 no tiene T0 y su entrada real está deshabilitada. Recovery preserva
multiplicidad y RECOVERED_AFTER_GAP hasta régimen normal; no demuestra continuidad perdida.
G4 necesita autorización separada, cinco sesiones completas, cierre/reapertura semanal,
rollover y revisión de toda la evidencia, incluidos fallos. No requiere órdenes/fills.
