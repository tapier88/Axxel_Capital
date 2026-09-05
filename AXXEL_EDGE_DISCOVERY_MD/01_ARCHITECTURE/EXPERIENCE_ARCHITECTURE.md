# EXPERIENCE ARCHITECTURE

## Contrato vigente de datos

Las experiencias de mercado son gold derivado de un dataset Data Engine elegible; padre, receta y SHA256 enlazan cada reconstrucción. El índice de experiencias y las memorias siguen siendo los existentes. El JSON mixto de mercado no es una vía de compatibilidad.

Representa experiencia como STATE → ACTION → OUTCOME.

## Contrato V0

Cada episodio contiene ID, fecha UTC, `hypothesis_id`, `experiment_id`, state, action, outcome, confianza y tags. Se almacena en `experience_store/episodes.json`; los IDs duplicados son rechazados y cada escritura reemplaza el documento atómicamente.
