# AXXEL CAPITAL

AXXEL CAPITAL es un proyecto de investigación cuantitativa reproducible y evolución
aditiva de capacidades. Su misión es descubrir, falsar y documentar relaciones útiles
sin confundir resultados históricos, calidad de software y autorización de trading.
North Star: **REPRODUCIBLE_RISK_ADJUSTED_NET_EDGE**. Gobierno: HUMAN_ON_THE_LOOP.

## Estado actual

| Área | Estado vigente |
|---|---|
| Fase | PHASE_1_FOUNDATION |
| Cuello de botella | G3_HISTORICAL_ROUTE_AND_G4_XM_FORWARD_QUALIFICATION |
| Track A / G3 | NOT_ESTABLISHED |
| Track B V1 | BLOCKED_AND_REVOKED_FOR_QUALIFICATION; evidencia preservada |
| Track B V2 | IMPLEMENTED_AWAITING_START_APPROVAL; readiness BLOCKED |
| V2 activation / T0 / G4 | false / null / false |
| XM legacy / HistData | EXPLORATORY_ONLY / EXPLORATORY_ONLY |
| Data Engine | IMPLEMENTED; DATA_ENGINE_CERTIFIED=false |
| Control Tower | BLOCKED; no avance a PHASE_2 |

No hay una estrategia autorizada para operar ni una fundación de datos certificada.
El código de Data Engine, contratos de alcance, research/ML y pruebas existe;
las capas autónomas del roadmap no están desplegadas. Los resultados científicos
históricos se conservan como evidencia, incluidos rechazos e incidentes.

## Arquitectura y lectura

1. [Estado del proyecto](docs/PROJECT_STATUS.md).
2. [Arquitectura canónica](.axxel/master_architecture/README.md) y
   [estado canónico](.axxel/master_architecture/13_STATE/AXXEL_STATE.json).
3. [Arquitectura implementada y futura](docs/ARCHITECTURE.md).
4. [Flujos](docs/EXECUTION_FLOW.md), [datos](docs/DATA_FOUNDATION.md) y
   [gobierno](docs/GOVERNANCE.md).
5. [Roadmap](docs/ROADMAP.md), [bloqueos](docs/GAPS_AND_BLOCKERS.md) y
   [auditoría del flujo](docs/FLOW_AUDIT.md).
6. [Árbol real](docs/PROJECT_TREE.md) y [política de publicación](docs/REPOSITORY_POLICY.md).

La fuente de verdad es `.axxel/master_architecture/`. El ZIP es derivado y el agente
lo regenera después de cambios aprobados; nunca reemplaza snapshots históricos.
El corpus AXXEL_EDGE_DISCOVERY_MD conserva contratos y diseños científicos anteriores;
los informes fechados son históricos, no permisos actuales.

## Reproducción segura

Entorno auditado: Windows, Python 3.13. Pruebas de cálculo sintéticas y comprobaciones
documentales de evidencia agregada preservada; no se necesitan credenciales ni datasets.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test-lock.txt
python -m pip install -e . --no-deps
python -m pytest tests -q
python scripts/package_master_architecture.py
```

Los locks declaran versiones, no hashes de todas las ruedas transitivas; el informe
publicado registra el entorno efectivamente probado. Las pruebas Windows específicas
no equivalen a validación del host durante cinco sesiones ni a resistencia a corte eléctrico.
No ejecutar scripts de adquisición, research o VALIDATION para probar la instalación.

## Próximos pasos y seguridad

Cerrar la revisión documental de esta baseline; luego abordar G3 y los bloqueos de
readiness G4 en tareas acotadas. No comprar datos ni iniciar V2 por publicar este repo.
Control Tower requiere evidencia del gate de Foundation y aprobación posterior.
RAW, ticks, holdouts, modelos, credenciales, logs de host y configuración local están
excluidos de Git. No usar fuerza para agregarlos. No promoción automática, no nuevo T0,
no órdenes, no trading, no fills y no apertura de VALIDATION/LOCKED_OOS.
