# AGENT CONTRACT

## Contrato mínimo de cada tarea

```yaml
task_id: ""
objective: ""
why_now: ""
phase: ""
depends_on: []
blocked_by: []
allowed_paths: []
protected_paths: []
inputs: []
outputs: []
tests_required: []
metrics_required: []
acceptance_criteria: []
rollback_plan: ""
max_scope: ""
```

---

# Norma de alcance

Una tarea debe ser:

- pequeña;
- medible;
- reversible;
- testeable;
- conectada al cuello de botella.

El agente no debe ejecutar "mejorar todo AXXEL".

Debe ejecutar tareas del tipo:

`DATA-017 — validar continuidad temporal M1 por símbolo y generar evidence artifact`

---

# Declaración de completitud

Una tarea es `DONE` solo si:

1. existe artefacto;
2. tests pasan;
3. acceptance criteria pasan;
4. el estado fue actualizado;
5. existe evidencia;
6. no se violó ningún gate;
7. se registraron riesgos y lecciones.
