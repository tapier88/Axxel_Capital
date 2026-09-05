# EVALUATION ENGINE

## No basta con "funcionó"

Cada tarea necesita criterios cuantitativos.

---

# Métricas maestras

## Reliability

```text
correct_validated_outputs / total_outputs
```

## Autonomy

```text
tasks_completed_without_human_intervention / eligible_tasks
```

## Intervention Rate

```text
human_interventions / eligible_tasks
```

## Validated Throughput

```text
validated_useful_outputs / unit_time
```

## Cost Efficiency

```text
validated_value / total_compute_and_execution_cost
```

## Failure Recurrence

```text
repeated_known_failures / total_failures
```

Debe tender a cero.

## Learning Rate

```text
reduction_in_repeated_failures_after_lessons
```

## Improvement Velocity

```text
validated_improvements / unit_time
```

---

# Trading-specific evaluator

Una estrategia NO puede evaluarse solo por PnL.

Debe considerar al menos:

- OOS;
- walk-forward;
- drawdown;
- robustness;
- regime consistency;
- costs;
- slippage;
- parameter sensitivity;
- Monte Carlo;
- opportunity frequency;
- sample size;
- risk-adjusted return;
- net expectancy.

Promoción solo si mejora OOS sin empeorar robustez, drawdown, estabilidad, ejecución o riesgo.


---

## Ablation tests

AXXEL must validate whether an added input, metadata field, tool, or context element
actually improves performance.

For any material architectural input:

```text
FULL SYSTEM
vs
ABLATION WITHOUT COMPONENT
```

Measure:
- reliability;
- success rate;
- validated throughput;
- latency;
- cost;
- intervention rate.

Do not keep architectural complexity that does not produce measurable lift.

---

## Metadata x Data-Quality Ablation

When heterogeneous or lower-quality experience is used, AXXEL should compare:

```text
A. HIGH-QUALITY DATA ONLY
B. HIGH + LOW-QUALITY DATA, WITHOUT METADATA CONDITIONING
C. HIGH + LOW-QUALITY DATA, WITH METADATA CONDITIONING
```

Evaluate on held-out tasks.

Interpretation:

- If B < A but C > A, metadata is enabling useful extraction from otherwise harmful noisy data.
- If C ≈ B, metadata is not contributing enough and should not justify extra complexity.
- If both B and C < A, the low-quality data should remain diagnostic only and not be used for learning.

Track:

```text
METADATA_LIFT_ON_NOISY_DATA =
performance(C) - performance(B)
```

and:

```text
LOW_QUALITY_DATA_NET_VALUE =
performance(C) - performance(A)
```

This prevents AXXEL from adding noisy data merely because more data is available.

