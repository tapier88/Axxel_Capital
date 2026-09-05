# RETRIEVAL ARCHITECTURE

Recuperación selectiva de recuerdos relevantes antes de decidir.

## V0

Tokeniza pregunta, contenido y tags; combina similitud Jaccard (80 %) con confianza (20 %), ordena y devuelve hasta diez resultados. Consulta working, episodic, semantic, long-term y episodios originales. La puntuación es interpretable, pero no equivale a comprensión semántica.
