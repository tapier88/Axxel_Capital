# Governance

HUMAN_ON_THE_LOOP: el humano aprueba cambios de alcance, gates, operación y promoción.
Arquitectura aditiva; baseline validada protegida por defecto. El agente observa,
documenta, implementa solo lo autorizado y aporta pruebas/evidencia.

Default deny: sin autorización de uso/campo/tiempo/entorno se deniega antes de I/O.
STOP ante falta de evidencia, contradicción sin autoridad para resolver, fallo crítico,
riesgo a componentes protegidos, intento de abrir holdouts o trading no autorizado.
No promoción automática. No rebajar thresholds para pasar tests ni limpiar falsaciones.

Gates G1…G6 del ADR son conjuntivos; readiness no equivale a DATA_ENGINE_CERTIFIED.
Control Tower y PHASE_2 siguen bloqueados. GitHub no cambia ningún permiso científico.
Toda captura nueva necesita acta independiente y T0 durable; V1 no se rehabilita.

Rollback de documentación/código mediante un commit inverso revisado, conservando
historial. Nunca revertir evidence/estado operacional a un punto que borre revocación
ni sobrescribir RAW. Guardar snapshots previos localmente y registrar cada cambio.

La fuente canónica es .axxel/master_architecture/. El agente ejecuta el empaquetador
después de cambios aprobados del master y registra hashes; ZIP siempre derivado.
La publicación usa rama de preparación, revisión del índice y push sin force.
Credenciales y datos privados nunca se agregan aunque .gitignore pueda forzarse.
