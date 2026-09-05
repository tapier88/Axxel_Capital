# PROTECTED BASELINE

## Objetivo

Evitar que AXXEL V2 destruya el valor acumulado en V1.

---

# Principio

Toda capacidad previamente validada se considera:

`PROTECTED_BY_DEFAULT`

---

# Está prohibido

Sin proceso de cambio formal:

- eliminar carpetas existentes;
- renombrar masivamente módulos;
- reescribir tests para hacerlos pasar;
- reducir gates de riesgo;
- borrar logs/evidencia;
- cambiar splits históricos para mejorar resultados;
- usar OOS bloqueado durante discovery;
- eliminar rollback;
- habilitar ejecución real;
- mover credenciales al frontend;
- reducir aislamiento entre research, risk, execution y clientes;
- convertir una propuesta en producción sin validación.

---

# Política de cambio

```text
OBSERVE
  ↓
DOCUMENT
  ↓
PROPOSE
  ↓
SHADOW
  ↓
SANDBOX
  ↓
CHALLENGER
  ↓
VALIDATE
  ↓
PROMOTE
```

En cualquier punto:

`FAIL → REJECT / ROLLBACK`

---

# Baseline técnico conocido

La lista siguiente es ilustrativa del diseno original, NO inventario implementado.
El arbol real vigente esta en 00_START_HERE/PROJECT_TREE.md:

```text
.cloud/
scripts/
config/
data/
python/
models/
mql5/
journal/
reports/
.agent_memory/
tests/
docs/
```

V2 no obliga a mover estos directorios.

La arquitectura V2 puede convivir con ellos mediante capas nuevas.
