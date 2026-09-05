# MIGRATION NOTE

## Contrato vigente de datos

La entrada de mercado vigente es Data Engine dentro de `src/data`, reutilizando Experience Store y el flujo científico existente. No hay compatibilidad de lectura para RAW/JSON/históricos sin certificado: se requiere una nueva versión auditada. Se conservan archivos, evidencia negativa e incidencia de particiones. El piloto parcial queda EXPLORATORY_ONLY; no se cambia el pre-registro ML para forzar su ejecución.

Esta arquitectura amplía la estructura existente sin eliminarla. Integrar progresivamente: CORE → ARCHITECTURE → MEMORY → DATA/EXPERIENCE → RESEARCH/VALIDATION → VALUE → EXECUTION.
