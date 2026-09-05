# EXPERIENCE + LEARNING

## Objetivo

Convertir trabajo real en memoria útil.

---

# Tipos de experiencia

## SUCCESS
Qué contexto + decisión produjo un resultado validado.

## FAILURE
Qué falló, impacto, evidencia y root cause provisional.

## INTERVENTION
Qué decisión tomó el sistema, qué corrigió el humano y por qué.

## DISCOVERY
Qué patrón, proceso o herramienta produjo una mejora medible.

---

# Experience Schema

```yaml
experience_id:
timestamp:
task_id:
context:
decision:
action:
result:
expected_result:
metrics:
status:
failure_type:
human_intervention:
root_cause:
lesson:
reusability_scope:
confidence:
evidence_refs:
```

---

# Lesson extraction

No toda experiencia genera una regla.

Una lección requiere:

- evidencia suficiente;
- recurrencia o impacto alto;
- mecanismo plausible;
- ausencia de contradicción crítica.

---

# Policy Memory

Las políticas aprendidas se guardan versionadas.

Ejemplo:

```yaml
policy_id: COST_GATE_003
version: 2
rule: >
  reject additional compute allocation when estimated executable
  edge is not materially above transaction-cost uncertainty.
evidence_count: 14
status: challenger
```

---

# Recipe Engine

Una receta es un proceso operativo completo.

Ejemplo research:

```text
DATA CERTIFICATION
→ BASE RATE
→ HYPOTHESIS
→ UNCONDITIONAL TEST
→ CONDITIONAL TEST
→ COST REALITY
→ REGIME TEST
→ WALK-FORWARD
→ OOS
→ STRESS
→ DECISION
```

Las recetas también tienen champion/challenger.


---

## Policy rollout experience

Every meaningful attempt by the agent generates an experience record:

```text
TASK → ACTIONS → TRACE → OUTCOME → EVALUATION → EXPERIENCE
```

Preserve both successful and failed trajectories.

Required metadata:
- task/subtask;
- model/policy/recipe version;
- tools used;
- outcome;
- failure type;
- intervention;
- quality/confidence;
- evidence refs.

This is used by the Learning Engine, not treated as automatically trusted training data.

---

## Metadata-conditioned use of low-quality experience

AXXEL must not assume that low-quality experience is useless.

The key distinction is whether the system knows enough metadata to interpret that experience correctly.

Low-quality records can become useful when they are accompanied by context such as:

- source;
- task/subtask instruction;
- quality tier;
- quality score;
- confidence;
- success/failure outcome;
- episode duration;
- intervention count;
- model/policy/recipe version;
- environment/regime;
- provenance;
- completeness.

### Rule

```text
LOW-QUALITY DATA
+ NO CONTEXT
→ can degrade learning

LOW-QUALITY DATA
+ RICH METADATA / INSTRUCTIONS
→ may add useful signal
```

Therefore, AXXEL must separate:

```text
DATA QUALITY
from
DATA INTERPRETABILITY
```

A lower-quality trajectory is not automatically discarded if its metadata makes its limitations explicit.

### Learning weight

A simple auditable weighting rule may use:

```text
learning_weight =
quality_score
× confidence
× metadata_completeness
× relevance
× outcome_verifiability
```

This is a policy input, not a claim that one fixed formula is universally optimal.

### Gate

Low-quality experience may enter the learning pool only when:

1. provenance is known;
2. quality tier is explicit;
3. instruction/task context is present when required;
4. metadata completeness passes threshold;
5. it cannot contaminate certified research evidence;
6. ablation shows net positive value.

