# Auditoría de arquitectura V0

Fecha: 2026-09-02. Alcance: Prompt #1.

## Hallazgos preservados

- La arquitectura de directorios era coherente como mapa conceptual, pero todos los módulos Python y scripts eran esqueletos de una línea.
- `state/*.json` existía con estructura mínima; no había código que lo leyera o persistiera.
- Los directorios documentales y ejecutables de hipótesis, experimentos y memoria se solapan intencionalmente: `AXXEL_EDGE_DISCOVERY_MD` es documentación; los directorios raíz son almacenamiento operativo. No se eliminó ninguno.
- No se detectaron enlaces Markdown internos rotos porque la documentación inicial no contenía enlaces. Sí había una contradicción de madurez: nombres de componentes completos frente a ausencia total de implementación. Se resuelve marcando explícitamente V0 versus esqueleto.
- La configuración declaraba `autonomous_research` mientras el requisito exige `RESEARCH_ONLY`; se preserva el propósito autónomo, pero el modo operativo se normalizó a `RESEARCH_ONLY`.
- Los endpoints MCP suministrados contenían sintaxis Markdown dentro de URLs. Se normalizaron en los archivos locales. `terminal` responde en el puerto local; `metaeditor` no respondió durante la auditoría; el host de `marketdata` resuelve por DNS. No se llamó a herramientas de trading.
- El directorio no es un repositorio Git, por lo que no existe historial/versionado local verificable. El registro de esta auditoría actúa como changelog inicial, no como sustituto de control de versiones.
- La consola mostró caracteres españoles con una representación incorrecta durante el dry-run; una lectura posterior de los archivos confirmó que la persistencia UTF-8 conserva correctamente `¿`, `ó` e `í`. Es un artefacto de salida de terminal, no corrupción del almacenamiento.

## Implementado

- Escritura JSON atómica y migración no destructiva por mezcla de defaults.
- Estados persistentes: agent, research, experiment, memory y value model.
- IDs UTC + UUID para HYPOTHESIS, EXPERIMENT, EPISODE, MEMORY y MODEL_VERSION.
- Registros append-only lógicos con rechazo de IDs duplicados.
- Memoria working acotada, episodic enlazada a episodios, semantic consolidada y long-term promovida por umbral.
- Retrieval léxico transparente sobre las cuatro escalas y episodios.
- Consolidación por hipótesis, con umbral configurable y enlaces a toda evidencia fuente.
- Uncertainty, information value y research value V0 acotados a `[0,1]`.
- Autonomous loop completo con validación estructural y ejecución fail-closed.

## Conflictos e incertidumbres

- Una consolidación V0 indica evidencia acumulada, no verdad de mercado ni edge validado.
- La persistencia JSON atómica protege cada archivo, pero no ofrece transacciones entre varios archivos ni bloqueo multiproceso.
- Retrieval léxico no comprende sinónimos, negación ni contexto temporal.
- No hay dataset, contrato de broker, terminal MetaEditor disponible ni evidencia estadística. Estas ausencias se registran como incertidumbre, no se completan con supuestos.
- Las credenciales MCP fueron proporcionadas en texto y deben rotarse si este canal o equipo no es completamente confiable.

## Esqueletos pendientes

Data ingestion/quality/features, discovery/prioritization/counterfactual, validación estadística completa, replay, calibration/reward/trade value, scheduler/router, recovery, risk/kill switch/MT5 bridge y toda la carpeta MQL5.

## Decisiones

- Sin SQLite ni embeddings en V0: JSON atómico facilita auditoría y mantiene cero dependencias.
- Ninguna promoción automática. `promotion_state.json` permanece en `IDEA`.
- Ninguna prueba de flujo se presenta como validación de estrategia.

## Evidencia de arranque

- Dos iteraciones completas fueron persistidas sobre la misma hipótesis.
- La segunda recuperó tres registros previos y consolidó dos episodios en una memoria semántica.
- Estado final observado: iteración 2; working 2; episodic 2; semantic 1; long-term 0.
- La ausencia de long-term es correcta: aún no se alcanza el umbral de cuatro episodios ni confianza 0.75.
- Ocho pruebas automatizadas pasan y todos los módulos editados compilan.
