# IMPROVEMENT ENGINE

## Pregunta central

> ¿Cuál es el cuello de botella que más limita el objetivo maestro ahora?

---

# Inputs

- metrics;
- failures;
- intervention history;
- cost;
- run duration;
- blocked tasks;
- reliability;
- architecture gaps;
- business/trading value.

---

# Output

Una lista priorizada:

```yaml
- improvement_id:
  problem:
  evidence:
  root_cause:
  expected_impact:
  effort:
  risk:
  dependencies:
  proposed_challenger:
  validation_plan:
```

---

# Priorización

Usar una función similar a:

```text
Priority =
ExpectedImpact
× Confidence
× StrategicAlignment
÷ (Effort × Risk × DependencyCost)
```

No tiene que ser financieramente exacta.

Debe ser consistente y auditable.

---

# Failure escalation

```text
FIRST OCCURRENCE
→ log

REPEAT
→ correlate

CLUSTER
→ root cause analysis

SYSTEMATIC
→ process gap

STRUCTURAL
→ architecture gap
```
