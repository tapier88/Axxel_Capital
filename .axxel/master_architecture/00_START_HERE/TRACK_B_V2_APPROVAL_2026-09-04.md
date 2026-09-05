# TRACK B V2 — Human decision

Date: 2026-09-04

Decision: **APPROVED FOR IMPLEMENTATION ONLY**

Approved:
- Implement V2 inside the existing Data Engine.
- Preserve V1 as blocked/revoked qualification evidence.
- Add durable recovery episode semantics, persistent RECOVERED_AFTER_GAP, worker heartbeat,
  OS sleep/resume observation, per-stage timestamps, immutable checkpoint journal and UTC fail-closed behavior.
- Execute synthetic/fault-injection and Windows durability tests.

Not approved:
- No new T0.
- No market capture.
- No trading/orders/fills.
- No research.
- No VALIDATION or LOCKED_OOS access.
- No promotion of XM legacy or HistData.
- No G4 pass and no DATA_ENGINE_CERTIFIED=true.

Before any future T0:
- exact local non-synced storage path must be preregistered;
- host uptime/sleep policy must be verified;
- DEMO identity must be rebound;
- frozen V2 config/code/host/account/path hashes must be reviewed;
- separate human start authorization is required.
