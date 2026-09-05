# ARCHITECTURE EVOLUTION CONSTITUTION

## Regla 1 — Preservación

Lo validado se preserva.

## Regla 2 — Evidencia

No existe cambio arquitectónico sin evidencia del gap.

## Regla 3 — Aditivo primero

Toda capacidad nueva debe ser añadida en paralelo cuando sea posible.

## Regla 4 — Reversibilidad

Toda promoción requiere rollback.

## Regla 5 — Champion/Challenger

Un challenger reemplaza al champion solo con evidencia superior.

## Regla 6 — Human gate

Cambios de alto impacto requieren aprobación humana.

---

# Architecture Gap Schema

```yaml
gap_id:
detected_at:
symptoms:
affected_tasks:
failure_count:
root_cause_evidence:
missing_capability:
current_workaround:
business_impact:
risk_impact:
priority:
proposed_component:
acceptance_test:
status:
```

---

# Tipos de gap

- missing_data;
- missing_tool;
- missing_model;
- missing_process;
- missing_observability;
- missing_governance;
- missing_recovery;
- missing_execution_capability;
- missing_risk_capability;
- missing_business_capability.
