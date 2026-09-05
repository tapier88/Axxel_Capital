# RESEARCH + TRADING ARCHITECTURE

## Principio

AXXEL no es un bot de indicadores.

Es un laboratorio cuantitativo con camino controlado hacia ejecución.

---

# Pipeline

```text
DATA
→ CERTIFICATION
→ OPPORTUNITY DISCOVERY
→ HYPOTHESIS PREREGISTRATION
→ EXPERIMENT
→ SKEPTIC
→ MULTIPLE-TEST CONTROL
→ WALK-FORWARD
→ OOS
→ COST REALITY
→ STRESS
→ RISK
→ LIFECYCLE DECISION
```

---

# Lifecycle

```text
IDEA
DISCOVERY
DEV
VALIDATION
SHADOW
DEMO
PRODUCTION_CANDIDATE
LIVE
RETIRED
```

No se puede saltar etapas.

---

# Trading gates

Bloquear promoción si:

- mejora solo train;
- empeora drawdown;
- falla walk-forward;
- comportamiento fuera de rango;
- robustez débil;
- Monte Carlo débil;
- risk noncompliance;
- coste destruye edge;
- OOS insuficiente;
- evidencia estadística insuficiente.

---

# Cost reality

Mientras la cobertura histórica bid/ask/tick sea incompleta:

- etiquetar confianza;
- separar REAL_TICK_COST de PROXY_COST;
- nunca ocultar la degradación;
- evitar conclusiones económicas excesivas.
