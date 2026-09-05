# EXECUTION ENGINE

## Objetivo

Convertir tareas declarativas en ejecuciones reproducibles.

---

# Componentes

### Task Queue
Estados permitidos:

```text
BACKLOG
READY
RUNNING
BLOCKED
REVIEW
DONE
REJECTED
ROLLBACK
```

### Dependency Graph
Ninguna tarea corre si una dependencia no está `DONE`.

### Resource Budget
Cada tarea puede limitar:

- tiempo;
- tokens;
- CPU/GPU;
- broker calls;
- data reads;
- risk exposure.

### Artifact Registry
Todo output importante debe poder ser localizado.

### Run Manifest

Cada ejecución genera:

```json
{
  "run_id": "",
  "task_id": "",
  "started_at": "",
  "ended_at": "",
  "commit_before": "",
  "commit_after": "",
  "inputs": [],
  "outputs": [],
  "tests": [],
  "metrics": {},
  "status": ""
}
```
