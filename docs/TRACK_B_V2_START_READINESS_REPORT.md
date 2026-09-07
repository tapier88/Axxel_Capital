# Track B V2: revisión de preparación de arranque

Resultado: **TRACK_B_V2_START_READINESS_BLOCKED**.
Baseline de código: `817908b0fc5fa7c4967ee61401177e90b51f096f`.
No se inició captura, no se creó T0 ni se solicitaron ticks, histórico u órdenes.

PHASE_1_FOUNDATION; G3/G4 siguen bloqueados. Esta revisión no modifica Track A,
XM legacy, HistData ni el exit gate de Foundation. Siguiente acción: revisar y
aprobar por separado los cambios operacionales pendientes.

| Área | Resultado |
|---|---|
| Storage | DEGRADED: candidato `C:\AXXEL\Data\TrackB\XMForwardV2`; NTFS local fijo sobre SSD NVMe, 42.23 GiB libres al observar. Escritura, flush/fsync, publicación exclusiva y lock entre procesos pasan. Fuera del root OneDrive observado y sin reparse en ancestros; atestación completa de sync pendiente. Ruta propuesta, no aprobada ni aplicada a config. |
| Energía | BLOCKED: sleep AC=900/DC=600 s; hibernate AC/DC=10800 s; tapa suspende. Plan Equilibrado. Sin cambios aplicados. |
| Wake/reinicios | Consultas requests/waketimers requieren administrador. No señales de reinicio pendiente en las dos claves CBS/WU comprobadas; active hours 07–00. Esto no garantiza uptime continuo. |
| XM DEMO | DEGRADED: XMGlobal-MT5 6 / XM Global Limited / DEMO conectado; build 6159, MT5 5.0.5430. Fingerprint server:login coincide con el previo. GOLD/XAUUSD actual no acreditado sin una llamada capaz de devolver cotizaciones. |
| UTC | READY solo en la observación: Cloudflare y Google respondieron; desacuerdo 2.003 ms, incertidumbre 33.523 ms. Revalidación obligatoria al arrancar. |
| Procesos/lock | DEGRADED: entrypoints de captura V1/V2 no observados; monitor V1 PAUSED; revocación vigente y lock de prueba pasa. Supervisor operacional V2 pendiente. Los procesos de prueba fueron exclusivamente sintéticos. |
| Performance | BLOCKED: 279 lotes medidos de 384 previstos; repetidos lotes de 41–47 s incumplen el criterio preregistrado de 30 s. |
| Ceremonia | BLOCKED: diseño A–N y 13 pruebas negativas de arranque; la ceremonia operacional completa no está implementada. K–N no ejecutados. |

El reloj local estaba adelantado unos 3,7 s en la observación UTC y Windows Time
estaba detenido; no se corrigió. Se registraron DNS, wall y monotonic. UDP tiene
timeout 2 s; getaddrinfo no tiene timeout explícito y SNTP no autentica la fuente.
No se validan retrospectivamente periodos anteriores ni se rebajan tolerancias.

## Escala medida y limitaciones

Preregistro: 384 lotes, tres filas repetidas por lote, clock sintético de 30 s,
límite de ejecución 3600 s. Worker y parámetros operacionales sin cambios; corpus
en temporal local C: NTFS, distinto de la ruta candidata. No fue un host aislado.

| Secuencia | Lote s | Reconcile integral s | Lookup journal ms | Bytes durables |
|---|---|---|---|---|
| 1 | 0.282 | 0.004 | 0.247 | 19878 |
| 32 | 0.627 | 0.157 | 0.531 | 597104 |
| 64 | 0.859 | 0.287 | 0.419 | 1207503 |
| 128 | 1.567 | 0.717 | 0.336 | 2443510 |
| 192 | 2.784 | 1.379 | 0.265 | 3716880 |
| 256 | 5.356 | 2.437 | 0.708 | 4998457 |

Máximo observado por lote: 47.139 s.
Tiempo hasta el último lote registrado: 814.811 s.
RSS pico muestreado: 133.50 MiB.
CPU, I/O acumulado y latencia real de heartbeat del ensayo completo: **NO DISPONIBLES**;
los contadores en memoria no se persistieron antes de la interrupción. No se inventan
valores cero ni se sustituyen por el reloj sintético de los eventos.

La prueba r2 quedó incompleta a 151 lotes, causa UNKNOWN. r3 falló en el contador
del harness por un archivo .partial transitorio del heartbeat; se corrigió solo
ese contador y se preservó el fallo. r4 se detuvo tras 279 lotes
medidos por el incumplimiento repetido de cadencia; no emitió resumen final. Su
log incremental y corpus permanecen conservados, y la causa concreta de los picos
es UNKNOWN. Una muestra puntual de CPU global y RAM no demuestra causalidad.

El intento posterior de medir recuperación del último checkpoint también quedó
sin resultado final, proceso ausente y causa UNKNOWN. El checkpoint original
retirado **solo del corpus sintético** está preservado aparte; no se afirma
reconstrucción ni recuperación completa. Las pruebas integradas de recovery de
la suite no sustituyen esa medición a escala pendiente.

Escenario ilustrativo, no calendario del broker: 5 × 24 h / 30 s = 14.400 lotes.
Una proyección lineal desde el último reconcile medido daría
137.1 s por reconcile:
**extrapolación, no medición**. Hay reconciliación antes y después de cada lote,
y búsqueda de receipts recorriendo eventos por cada derived. Tres filas por lote
subestiman payload real. No es razonable autorizar cinco sesiones con esta evidencia.
Se requiere revisar rendimiento y medición durable bajo autorización separada,
conservando todas las verificaciones y los parámetros congelados.

## Pruebas y preservación

Suite completa actual: **344 passed**, cero failures/errors/skips. Incluye las
44 pruebas integradas V2 y 13 nuevas negativas de entrada. Cubre lock, journal,
recovery, heartbeat, Windows durability, fault injection y denegaciones de
Track A/research/VALIDATION/LOCKED_OOS mediante fixtures. No se leen holdouts reales.
El gate de rendimiento falló aunque estas pruebas funcionales pasen.

V1: 2676 artefactos verificados por hash e inventario idénticos, más
código/config protegidos intactos. V1 sigue revocada con T0 original
`2026-09-04T19:18:39.974001Z`. Código de producción y configuración V2 coinciden
con los hashes aceptados; no se alteraron tests anteriores para hacerlos pasar.

Nuevo preregistro privado versionado:
`reports/track_b_xm_forward_capture_v2/start_readiness_r3/TRACK_B_V2_START_PREREGISTRATION.json`.
Estado PREPARED_NOT_AUTHORIZED; SHA256 `af36fc119a81ede0e457d088a8408eacb46a2f069b4c06c75144dbafbf956f19`.
Config SHA256 `afc49d5273841e8fafbfc083225114ff0193fec6e9b32480ac349abb52bc3d87`.
El preregistro anterior permanece intacto. Se registran commit de código, hashes,
dependencias, Python/psutil/MT5/build, Windows, host/cuenta no sensibles,
energía, storage, disco, UTC, supervisor, lock y retención. El commit final de
publicación documental se registra aparte para evitar autorreferencia circular.

[Resumen verificable](../reports/public_baseline/TRACK_B_V2_START_READINESS_20260907.json).
Evidencia completa local en start_readiness_r2/r3/r4; no se publica RAW ni metadata
privada del host. El agente regenera el ZIP maestro y registra ubicación/SHA en
`reports/public_baseline/TRACK_B_V2_READINESS_MASTER_EXPORT_20260907.json`.

## Acciones humanas y siguiente trabajo

Alex debe revisar el [checklist](TRACK_B_V2_START_CHECKLIST.md), acordar energía,
mantenimiento, sync y ruta, y autorizar por separado el trabajo operacional de
supervisor/ceremonia y rendimiento. El agente conserva before/after, repite pruebas
y readiness. Solo después podrá evaluarse autorización separada de captura/T0
ligada a un preregistro exacto. Aprobar este informe no habilita un flag de arranque.

Aprendizajes: persistir métricas incrementalmente; no confundir lookup rápido con
reconcile completo; conservar fallos y ausencias de medición; usar receta estable
de fingerprint; una denegación de mercado no demuestra una ceremonia operacional.

V2 activation=false; T0=null; G4=false; DATA_ENGINE_CERTIFIED=false; Control Tower
BLOCKED. G3 NOT_ESTABLISHED; XM legacy e HistData EXPLORATORY_ONLY. Trading,
orders, fills, slippage, research, VALIDATION y LOCKED_OOS siguen prohibidos.
