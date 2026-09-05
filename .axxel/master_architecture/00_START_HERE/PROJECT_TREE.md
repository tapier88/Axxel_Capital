# Real project tree

Inventory of existing top-level directories; existence does not imply phase promotion.

| Directory | Status/scope |
|---|---|
| .axxel/ | IMPLEMENTED: canonical architecture documents; target layers individually marked |
| .codex/ | SENSITIVE local tooling |
| .obsidian/ | LOCAL_ONLY editor settings |
| .pytest_cache/ | GENERATED cache |
| AXXEL_EDGE_DISCOVERY_MD/ | IMPLEMENTED documents: includes future scientific designs |
| config/ | IMPLEMENTED: frozen specs; no live authorization |
| data/ | LOCAL_ONLY: private payloads and runtime |
| docs/ | IMPLEMENTED executive documentation |
| experience_store/ | LOCAL_ONLY payloads; selected metadata published |
| experiments/ | LOCAL_ONLY runtime |
| hypotheses/ | IMPLEMENTED preserved preregistrations/registry |
| logs/ | LOCAL_ONLY logs |
| memory_db/ | PARTIAL existing modules/summaries; runtime private |
| models/ | GENERATED / LOCAL_ONLY |
| mql5/ | PLANNED: empty placeholder directories only |
| mql5_mcp_ea.egg-info/ | GENERATED packaging |
| reports/ | IMPLEMENTED evidence; reviewed public subset |
| scripts/ | IMPLEMENTED: guarded entrypoints and tooling |
| src/ | IMPLEMENTED/PARTIAL: code modules, not all target capabilities |
| state/ | Historical checkpoints; canonical governance state is separate |
| tests/ | IMPLEMENTED: synthetic and documentary regression suite |

## Implemented source areas

- src/data/
- src/execution/
- src/experience_store/
- src/memory/
- src/ml/
- src/orchestrator/
- src/research/
- src/utils/
- src/validation/
- src/value/

## Planned, no standalone implementation

Control Tower, general observability, integrated Learning/Improvement, Mission Control,
Generalist Intelligence and production EA remain planned/blocked. Empty mql5 folders
are placeholders. Do not infer a functional capability from a design document.

## Canonical master files

```text
00_START_HERE/AGENT_POSITION_AND_MISSION.md
00_START_HERE/ARCHITECTURE_AUDIT.md
00_START_HERE/ARCHITECTURE_DECISION_RULES.md
00_START_HERE/AXXEL_MASTER_PLAN_V2.md
00_START_HERE/FOUNDATION_RECOVERY_PLAN_ADR_001.md
00_START_HERE/MASTER_PACKAGE_MAINTENANCE.md
00_START_HERE/PROJECT_TREE.md
00_START_HERE/TRACK_B_STATE_RECONCILIATION_2026-09-04.md
00_START_HERE/TRACK_B_V2_APPROVAL_2026-09-04.md
00_START_HERE/TRACK_B_V2_IMPLEMENTATION_ACCEPTANCE_2026-09-04.md
01_CURRENT_SYSTEM/CURRENT_STATE.md
01_CURRENT_SYSTEM/PROTECTED_BASELINE.md
02_TARGET_ARCHITECTURE/TARGET_ARCHITECTURE.md
03_AGENT_OPERATING_MODEL/AGENT_CONTRACT.md
04_EXECUTION_ENGINE/EXECUTION_ENGINE.md
05_EVALUATION_ENGINE/EVALUATION_AND_METRICS.md
06_EXPERIENCE_LEARNING/EXPERIENCE_AND_LEARNING.md
07_IMPROVEMENT_ENGINE/IMPROVEMENT_ENGINE.md
08_ARCHITECTURE_EVOLUTION/ARCHITECTURE_EVOLUTION_CONSTITUTION.md
09_AUTONOMY_GOVERNANCE/AUTONOMY_AND_GOVERNANCE.md
10_OBSERVABILITY_MISSION_CONTROL/MISSION_CONTROL_SPEC.md
11_RESEARCH_TRADING/RESEARCH_AND_TRADING_ARCHITECTURE.md
12_ROADMAP_BACKLOG/DETAILED_TASK_BACKLOG.md
12_ROADMAP_BACKLOG/MASTER_ROADMAP.md
13_STATE/AXXEL_STATE.json
13_STATE/CAPABILITY_MATRIX.json
14_TEMPLATES/ARCHITECTURE_GAP_TEMPLATE.md
14_TEMPLATES/IMPROVEMENT_PROPOSAL_TEMPLATE.md
14_TEMPLATES/INTERVENTION_TEMPLATE.md
14_TEMPLATES/TASK_TEMPLATE.md
15_GENERALIST_INTELLIGENCE/GENERALIST_INTELLIGENCE_ARCHITECTURE.md
16_SHARED_DATA_FOUNDATION/SHARED_DATA_FOUNDATION.md
18_CONTEXT_AND_HIERARCHICAL_CONTROL/AGENT_CONTROL_LOOP.md
README.md
```
