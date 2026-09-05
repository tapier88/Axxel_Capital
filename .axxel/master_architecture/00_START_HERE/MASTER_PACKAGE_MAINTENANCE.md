# Mantenimiento del master canónico

Autorización: TRACK_B_V2_START_READINESS_REVIEW, decisión humana de esta tarea.
Fuente canónica: `.axxel/master_architecture/`. Ningún ZIP sustituye esta fuente.

Después de un cambio aprobado de arquitectura, estado, roadmap, gates, contratos,
ADR, fase, current_task o next_best_action, el agente ejecuta automáticamente como
parte del cierre: `python scripts/package_master_architecture.py`.
No es un watcher ni servicio: es una obligación del flujo de trabajo del agente,
registrada también en AGENTS.md. No depende de una acción manual de Alex.

El script valida maestros obligatorios, JSON y referencias críticas explícitas del
master; inventaría todos sus archivos y hashes, fija fechas y atributos del ZIP,
verifica apertura y bytes de sus miembros, y registra timestamp, source state hash,
zip hash e inventario en manifest.json. No acredita validez semántica universal de
la arquitectura ni verifica payloads externos o holdouts.

Cada ejecución crea un directorio nuevo en reports/master_architecture_exports.
Dentro se publica AXXEL_MASTER_ARCHITECTURE_V2_UPDATED.zip. Nunca se reemplaza un
snapshot histórico. Fallo de validación/publicación bloquea el cierre documental.
La ruta y hash se reportan al humano y se conservan en el registro de evidencia.
