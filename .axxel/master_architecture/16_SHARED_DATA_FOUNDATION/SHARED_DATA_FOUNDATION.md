# SHARED DATA FOUNDATION

## Idea central

AXXEL no debe recolectar, limpiar, etiquetar y reconstruir datos desde cero para cada proyecto.

Eso produce:
- duplicación;
- costes innecesarios;
- inconsistencia;
- pérdida de conocimiento;
- tiempos de investigación más largos;
- datasets incompatibles;
- dificultad para transferir aprendizaje.

La arquitectura debe separar:

```text
SHARED DATA FOUNDATION
        ↓
REUSABLE REPRESENTATIONS
        ↓
PROJECT-SPECIFIC DATA
        ↓
TASK ADAPTATION
        ↓
EXPERIMENT / EXECUTION
```

---

# Principio

> COLLECT ONCE, CERTIFY ONCE, REUSE MANY TIMES.

Todo dataset reusable debe vivir en una capa compartida y versionada.

---

# Shared Data Foundation

Debe contener:

## Raw immutable data
Datos originales sin modificar.

## Canonical normalized data
Datos normalizados con esquemas estables.

## Certified datasets
Datasets que han pasado gates de integridad.

## Feature foundation
Features reutilizables y no específicas de una sola estrategia.

## Cost data
Bid/ask, spread, slippage, proxies y confidence.

## Event/fundamental data
Datos macro/eventos con provenance y PIT cuando existan.

## Metadata
Símbolo, broker, timezone, sesiones, frecuencia, origen y versión.

## Dataset lineage
De dónde salió cada columna y transformación.

---

# Data Reuse Policy

Antes de recolectar datos nuevos, el agente debe consultar:

1. ¿Existe ya el dataset?
2. ¿Existe una versión compatible?
3. ¿Está certificado?
4. ¿Puede transformarse sin fuga?
5. ¿Qué falta realmente?

Solo si la respuesta es negativa debe proponer nueva adquisición.

---

# Data Capability Registry

```yaml
dataset_id:
name:
domain:
symbols:
time_range:
frequency:
source:
broker:
schema_version:
certification_status:
cost_model:
pit_status:
known_gaps:
confidence:
hash:
lineage:
consumers:
```

---

# Project Data Contract

Cada proyecto declara solo el delta necesario:

```yaml
project_id:
required_datasets:
required_features:
additional_data_needed:
reason:
expected_value:
reuse_ratio:
```

---

# Métricas

## Data Reuse Ratio

```text
reused_certified_data / total_data_consumed
```

## New Data Acquisition Rate

```text
newly_acquired_data / total_data_consumed
```

## Data Duplication Rate

Debe tender a cero.

## Certification Reuse

Cuántos proyectos reutilizan un dataset ya certificado.

## Time-to-Experiment

Tiempo desde la idea hasta el primer experimento reproducible.

La Shared Data Foundation debe reducir esta métrica de forma material.

---

# Regla para trading

No descargar nuevamente XAUUSD/EURUSD/USDJPY para cada estrategia.

Usar una base canónica y certificada, y construir vistas/versiones específicas por experimento.

Ejemplo:

```text
XM RAW M1
   ↓
CANONICAL M1
   ↓
CERTIFIED MARKET DATASET
   ├── research view A
   ├── research view B
   ├── ML feature view
   ├── cost-analysis view
   └── execution-replay view
```

---

# Relación con aprendizaje generalista

El equivalente arquitectónico al preentrenamiento no tiene que ser solo entrenar pesos.

Para AXXEL también significa crear una base reutilizable de:

- datos;
- features;
- herramientas;
- conocimientos;
- experiencias;
- políticas;
- recetas.

Cada proyecto posterior debería comenzar desde esa base acumulada, no desde cero.

---

# Regla de creación de proyectos

```text
NEW PROJECT
   ↓
QUERY SHARED FOUNDATION
   ↓
REUSE AVAILABLE ASSETS
   ↓
IDENTIFY DELTA
   ↓
ACQUIRE / BUILD ONLY MISSING PIECES
   ↓
CERTIFY DELTA
   ↓
RETURN NEW REUSABLE ASSETS TO FOUNDATION
```

Así, cada proyecto debe hacer que el siguiente sea más barato, rápido y confiable.


---

## Heterogeneous quality tiers

AXXEL may retain data of different quality, but it must never mix trust levels.

```text
GOLD   = certified/high-confidence
SILVER = useful but incomplete/degraded
BRONZE = exploratory/noisy/failed attempts
```

Every record must carry:
- provenance;
- quality tier;
- confidence;
- dataset/version;
- known gaps.

Failed or low-quality data can be useful for diagnostics and learning,
but cannot silently enter certified research datasets.

---

## Data reuse rule

`COLLECT ONCE, CERTIFY ONCE, REUSE MANY TIMES`

New projects must:
1. query the shared foundation;
2. reuse certified assets;
3. identify only the missing delta;
4. acquire/certify that delta;
5. return reusable assets to the foundation.

The goal is to reduce time-to-experiment, not maximize raw data volume.


---

## Diversity is a quality dimension

Dataset quality is not only cleanliness or size.

AXXEL must also measure whether the data covers sufficiently different:
- assets;
- regimes;
- volatility conditions;
- sessions;
- task families;
- success/failure modes;
- tool paths;
- intervention patterns.

A smaller but more diverse dataset may be more useful for generalization than a larger,
highly repetitive dataset.

### Diversity metrics

```text
DATA_DIVERSITY_SCORE
TASK_FAMILY_COVERAGE
REGIME_COVERAGE
FAILURE_MODE_COVERAGE
SOURCE_DIVERSITY
```

These metrics must be recorded alongside dataset size.

### Rule

Do not maximize data volume blindly.

Prefer the smallest dataset that preserves:
- diversity;
- coverage;
- reliability;
- information content.

---

## Diversity ablation protocol

AXXEL must distinguish between the value of **data volume** and the value of **data diversity**.

For important reusable datasets, compare at least:

```text
A. FULL DATASET
B. FULL DATASET - MOST DIVERSE SLICE
C. FULL DATASET - RANDOM SLICE OF SIMILAR SIZE
```

Interpretation:

- If removing the diverse slice causes a much larger degradation than removing a random slice,
  the lost value comes primarily from diversity/coverage rather than raw sample count.
- If both degrade similarly, volume may be the dominant factor.
- If neither changes materially, the removed data may be redundant.

Measure on held-out/new tasks:

- reliability;
- success rate;
- generalization;
- validated throughput;
- failure recurrence.

This test should be used before deciding to acquire substantially more data.

