# ARCHITECTURE DECISION RULES

## Purpose

Not every useful idea becomes a new component.

Every proposed improvement must first be classified.

---

## Decision tree

```text
NEW IDEA
  ↓
Does it solve a concrete current/future AXXEL problem?
  ├── NO → do not add
  └── YES
       ↓
Can an existing component absorb it?
  ├── YES → update that component
  └── NO
       ↓
Does it require independent state, lifecycle, permissions or interfaces?
  ├── NO → keep as rule/metric inside existing component
  └── YES → propose new component
```

---

## A new top-level component is justified only if it owns at least one of:

- independent state;
- distinct lifecycle;
- clear API/interface;
- separate permissions;
- separate failure domain;
- independent scaling;
- explicit operational responsibility.

If not, it belongs inside an existing component.

---

## Examples

### "Generalist should use context"
Not a new engine by itself.
Belongs in `Context Compiler / Generalist Intelligence`.

### "Failed attempts are useful data"
Not a new top-level subsystem.
Belongs in `Experience Engine`.

### "Reuse datasets across projects"
Belongs in `Shared Data Foundation / Data Engine`.

### "Choose the next subtask"
Belongs in `Control Tower / Planner`.

### "Detect missing architectural capability"
This DOES justify a component because it owns a distinct lifecycle:
detect → evidence → proposal → challenger → validation → promotion.

---

## Mandatory rule

Architecture changes must reduce one of:
- risk;
- latency;
- cost;
- failure recurrence;
- human intervention;
- duplicated work;

or increase one of:
- reliability;
- throughput;
- reproducibility;
- autonomy;
- validated value.

Otherwise, do not add them.
