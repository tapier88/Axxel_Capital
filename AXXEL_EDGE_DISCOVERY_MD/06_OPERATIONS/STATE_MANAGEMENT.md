# STATE MANAGEMENT

Procedimiento operativo para state management.

## Estados V0

`agent_state`, `research_state`, `experiment_state`, `memory_state` y `value_model_state` se cargan con compatibilidad hacia los JSON mínimos existentes y se escriben atómicamente. `agent_state` contiene las invariantes `RESEARCH_ONLY`, `live_trading=false` y `automatic_promotion_to_live=false`. Una contradicción en esas invariantes detiene el loop.
