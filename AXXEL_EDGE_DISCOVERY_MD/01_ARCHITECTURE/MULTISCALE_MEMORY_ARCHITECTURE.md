# MULTISCALE MEMORY ARCHITECTURE

Memoria working, episódica, semántica y de largo plazo.

## Contrato V0

- Working: contexto reciente, con capacidad máxima.
- Episodic: narración enlazada a un episodio persistido.
- Semantic: resumen de varios episodios con todos sus `evidence_ids`.
- Long-term: promoción de memoria semántica solo al superar evidencia y confianza configuradas.

Los registros viven en `memory_db/<escala>/records.json`. Nada se borra durante consolidación.
