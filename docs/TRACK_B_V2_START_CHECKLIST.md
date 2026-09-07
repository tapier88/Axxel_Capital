# Track B V2: checklist previo al arranque

Estado: **PREPARED_NOT_AUTHORIZED**. Esta revisión no crea T0 ni autoriza mercado.
La implementación aceptada conserva su entrada real denegada. El diseño siguiente
requiere implementación operacional y pruebas independientes antes de autorizarlo.

| Responsable | Acción | Comprobación / condición de parada |
|---|---|---|
| AGENT | Conservar V1 revocada, T0 original y hashes; preparar expediente versionado. | STOP CONDITION: archivo V1 distinto, ausente o evidencia insuficiente. |
| AGENT | Medir storage, energía, identidad DEMO sin cotizaciones, UTC, procesos y escala sintética. | AUTOMATIC CHECK: ninguna llamada de ticks, histórico, órdenes o símbolo con campos de precio. |
| HUMAN | Alex revisa riesgos, ruta, cuenta, política de energía y mantenimiento del host. | STOP CONDITION: aprobación incompleta o distinta del preregistro. |
| HUMAN | Autorizar por separado los cambios operacionales necesarios y, posteriormente, el arranque. | No basta aprobar este checklist ni pasar un flag al CLI. |
| AGENT | Ejecutar cambios autorizados, conservar before/after y volver a verificar. | STOP CONDITION: código/config/dependencias distintos de los hashes aprobados. |
| AUTOMATIC CHECK | Ejecutar A–J en orden, bajo el mismo proceso y lock. | Fail closed ante ausencia, caducidad, cambio de identidad o error. |
| AUTOMATIC CHECK | Solo en futura tarea autorizada: K–M durables y N. | STOP CONDITION: autorización o recibos inválidos; nunca reconstruir un T0 perdido por inferencia. |

## Ceremonia A–N propuesta

Cada evidencia se vincula al hash del preregistro, commit, configuración, host,
cuenta, ruta, identidad PID/creation/boot y nonce de ejecución. No se aceptan
booleanos enviados por un consumer como autoridad. Las verificaciones volátiles
se repiten inmediatamente antes del primer request y después de reconectar.

Contrato propuesto para J: autorización verificable de Alex con identificador
único, hash del preregistro, alcance de captura DEMO, commit/config, host/cuenta/ruta,
nonce, emisión, expiración y revocación consultable. Su autenticidad debe comprobarse
contra una autoridad humana provisionada fuera de la entrada del consumer; el
worker no puede emitir su propia autorización. La implementación deberá fijar y
probar ese mecanismo antes de aprobar el arranque. Registrar consumo durable de
la autorización y rechazar replay; tras crash, reanudar únicamente el mismo
expediente/T0 verificado, con política explícita. Ningún fichero de autorización
humana se ha creado en esta revisión.

| Paso | Acción futura | Fallo que debe denegar el avance |
|---|---|---|
| A | Verificar commit y hashes de los archivos de ejecución, sin cambios locales. | Commit/hash distinto. |
| B | Verificar configuración congelada aprobada. | Cualquier delta o permiso ampliado. |
| C | Verificar Python, dependencias, paquete MT5 y terminal build. | Versión no preregistrada. |
| D | Verificar ruta canónica NTFS sin sync, ACL, espacio ≥5 GiB y publicación durable. | Redirección, sync, disco bajo o prueba fallida. |
| E | Verificar AC, sleep/hibernate automáticos deshabilitados y política de tapa/reinicio. | Cualquier suspensión automática habilitada o política desconocida. |
| F | Verificar XMGlobal-MT5 6, XM Global Limited, DEMO y fingerprint exacto. | Identidad desconectada/cambiada; símbolo no acreditado por vía sin cotizaciones. |
| G | Verificar UTC independiente contemporáneo conforme límites congelados. | Ausencia, stale, incertidumbre/desacuerdo fuera del límite. |
| H | Verificar V1 revocada y ausencia de otros workers/supervisores conflictivos. | PID vivo, identidad desconocida o monitor anterior activo. |
| I | Adquirir lock exclusivo y retenerlo hasta parada controlada. | Contención; nunca borrar un lock para forzar entrada. |
| J | Verificar autorización humana separada ligada al expediente, nonce y alcance. | Token ausente, repetido, revocado, vencido o para otro expediente. |
| K | Crear un único T0 V2 con evidencia UTC vigente. | No hay autorización válida o ya existe estado inconsistente. |
| L | Persistir T0 mediante publicación exclusiva después de flush/fsync. | Error de escritura, colisión o persistencia incierta. |
| M | Releer y verificar bytes/hash, vínculos y cadena de autorización. | Cualquier inconsistencia; conservar parciales y STOP. |
| N | Permitir únicamente la primera petición de mercado del alcance aprobado. | Requiere A–M válidos y lock todavía retenido; ninguna ruta alternativa. |

**K–N no se ejecutan en esta revisión.** Las trece pruebas negativas ejercitan la
entrada real actualmente denegada y comprueban que no tiene efectos de T0/red.
Esto demuestra la imposibilidad actual de N, pero no acredita una ceremonia
operacional A–N implementada. Tampoco prueba firma/caducidad/replay de un token
futuro: ese mecanismo y sus pruebas siguen pendientes.

Tras un crash en L/M: conservar todos los bytes, verificar el mismo T0 y exigir
revisión si hay ambigüedad; nunca generar otro T0 silenciosamente. UTC perdido
suspende elegibilidad temporal y nunca se valida retrospectivamente.

## Energía: comandos preparados, no ejecutados

Plan observado: `381b4222-f694-41f0-9685-ff5bb260df2e` (Equilibrado).
Antes de cambiarlo, guardar consultas completas y aprobar la política. Ejecutar
en contexto autorizado, registrar códigos de salida y consultar de nuevo:

```powershell
powercfg /setacvalueindex 381b4222-f694-41f0-9685-ff5bb260df2e SUB_SLEEP STANDBYIDLE 0
powercfg /setdcvalueindex 381b4222-f694-41f0-9685-ff5bb260df2e SUB_SLEEP STANDBYIDLE 0
powercfg /setacvalueindex 381b4222-f694-41f0-9685-ff5bb260df2e SUB_SLEEP HIBERNATEIDLE 0
powercfg /setdcvalueindex 381b4222-f694-41f0-9685-ff5bb260df2e SUB_SLEEP HIBERNATEIDLE 0
powercfg /setacvalueindex 381b4222-f694-41f0-9685-ff5bb260df2e SUB_BUTTONS LIDACTION 0
powercfg /setdcvalueindex 381b4222-f694-41f0-9685-ff5bb260df2e SUB_BUTTONS LIDACTION 0
powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e
powercfg /query SCHEME_CURRENT SUB_SLEEP
powercfg /qh SCHEME_CURRENT SUB_BUTTONS
powercfg /requests
powercfg /waketimers
```

Los valores de restauración observados son STANDBYIDLE AC=900/DC=600,
HIBERNATEIDLE AC/DC=10800 y LIDACTION AC/DC=1; restaurarlos requiere también
registro y autorización. No deshabilitar protecciones de batería crítica.
Las consultas de requests/waketimers requieren elevación en este host.
Windows Update sin reboot pendiente no garantiza cinco sesiones sin reinicio:
Alex debe acordar una ventana de mantenimiento y alimentación continua.

G3 sigue NOT_ESTABLISHED; XM legacy e HistData EXPLORATORY_ONLY. G4=false,
DATA_ENGINE_CERTIFIED=false y Control Tower BLOCKED. No se autorizan trading,
orders, fills, slippage, research, VALIDATION ni LOCKED_OOS.
