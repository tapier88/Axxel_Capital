# FOUNDATION_SCOPE_READINESS_V1 — SHADOW implementation report

**Result: `FOUNDATION_SCOPE_READINESS_V1_SHADOW_IMPLEMENTED`**  
Date: 2026-09-04. Authority: human-approved `ADR-FOUNDATION-001`. Scope:
implementation/test/documentation with synthetic fixtures only.

## Outcome and boundary

The existing Data Engine now absorbs a versioned scope validator and pre-I/O reader.
No new top-level subsystem, catalogue, issuer, worker, provider adapter or execution
framework was created. The integration is opt-in SHADOW. It does not enroll a real
dataset or migrate a production consumer.

Every request is default-deny and fully validates the requested capability, canonical
fields, half-open interval, exact instrument plus definition, environment, purpose,
consumer and partition across the complete parent graph. It checks current validity
and revocation on every use. This finishes before artifact path resolution, hashing,
payload reads or cache access. The ALLOW result is diagnostic and cannot be reused as
a bearer token.

The reader accepts only an exact pre-scoped physical fragment. It has no row-filter,
fallback, RAW, arbitrary-path or caller-selected cache interface. The declared whole
artifact must fit every ancestor. Its fixed SC1 path is checked after authorization,
then SHA256 is checked before and after the projected read. Cache hits return copies
and reauthorize the complete graph first.

Track A and Track B have disjoint capabilities, fields, purposes, partitions and
environments. Track A does not grant XM spreads, costs, fills or slippage. Track B
does not grant research, Discovery, features, labels, ML, walk-forward or backtest.
Track B cannot relabel DEV, VALIDATION or LOCKED_OOS. Cross-track joins are denied.

All registered derivatives inherit the intersection of capabilities, fields,
purposes, consumers, period and validity. Their track, environment, instrument and
partition must agree; all parent provenance references remain present. This covers
union, concat, select, copy, rename, cache, feature, label, experience and model
manifest operations. These operations register metadata only: no transforms, ML or
backtests were executed or built. A new ID and intermediate derivative cannot widen
rights. Parent revocation blocks descendants and cached descendants immediately.

## Trust model and limitations

The trusted host supplies already-resident synthetic root metadata once, including
the clock and bound principal. Consumers supply requests only. Root admission in this
version is restricted to fixture references and `SHADOW_ELIGIBLE`; this prevents any
claim that XM legacy or HistData was promoted. The API boundary is not an OS/Python
sandbox: arbitrary process owners remain trusted, as in the existing Data Engine.

The gate proves authorization ordering and permission algebra. It does not establish
external provenance, source custody, time semantics, sessions, instrument truth,
missing-data adjudication or data quality. It does not persist revocations across
processes. Durable production admission/revocation and audited root issuance remain
future work that must use existing architecture or return for review.

The V1 reader and its old DE1 contract remain intact; the full regression suite
passed. SC1 IDs are rejected before V1 manifest I/O. Old contracts without every new
field receive no new scope capability. Previously valid V1 use remains within its
original DEV contract and is not reinterpreted.

## Acceptance evidence

The dedicated matrix is `ALLOW_DENY_MATRIX.md`. `MANIFEST_CONTRACT.json` records the
closed versioned shape. `scope_tests_initial_failure.xml` (and its original
`scope_tests.xml` copy) preserves the initial run:
79 passed and one failed because an integrity failure was reported too generally.
The defect was corrected without weakening a gate. `relevant_tests.xml` reports
**134 passed**. `full_suite.xml` / `full_suite.log` report **253 passed**. Tests use
temporary synthetic Parquet fixtures; no repository historical dataset or holdout
was opened, hashed or queried.

Baseline hashes cover code/config/tests and separate hashes preserve existing
Foundation/data-integrity evidence without touching RAW or holdouts. `evidence_manifest.json`
contains final hashes and verification facts. No protected historical evidence,
threshold, partition, falsification or earlier result was changed.

## G1, G5 and G6

| Gate | Result in this delivery | Limit |
|---|---|---|
| G1 — Data Engine implemented and tested | **FULFILLED for implementation/test** | V1 plus SHADOW scope tests and 253-test regression pass; this does not satisfy G3/G4 or certify data |
| G5 — research/execution separation | **FULFILLED in SHADOW** | Negative fixtures prove disjoint semantics and joins; no Track B capture exists |
| G6 — consumers block outside certified scope | **FULFILLED in SHADOW** | Engine-owned pre-I/O API and tripwire tests; production consumers are not migrated and no real root is admitted |

The full Foundation readiness gate remains blocked because G3 (a valid route to a
certifiable historical research dataset) and G4 (qualified XM forward capture with
verifiable provenance) remain unmet. That limit prevents claiming G5/G6 operationally
against real data.

## Pending before Track B may begin

1. Human review this SHADOW evidence and threat/trust boundary.
2. Give a separate bounded authorization for read-only Track B work, identifying XM
   server/account class, exact symbol, permitted PAPER/DEMO context and T0. This task
   granted none of those.
3. Approve the preregistered operational parameters required by the ADR: poll/snapshot
   cadence, timeout, lag/backlog, batch size, retention and UTC uncertainty/tolerance.
4. Then implement and test the minimal capture worker under a separate task; qualify
   the required sessions/weekly closure-reopening and record all loss/restarts.
5. Establish durable reviewed provenance/root admission and revocation loading before
   any real Track B certificate can be eligible.

No acquisition, network access or trading occurred. No research model was trained or
evaluated and no market backtest ran; the mandatory full regression suite may execute
existing synthetic unit fixtures for those modules.
VALIDATION and LOCKED_OOS remained inaccessible. `XM_LEGACY = EXPLORATORY_ONLY` and
`HISTDATA = EXPLORATORY_ONLY`. `DATA_ENGINE_CERTIFIED = false`. Control Tower remains
blocked. The eight external-evidence blockers remain open and unchanged.

## Modified repository files

- `src/data/scope.py` — pure scope validation/intersection policy.
- `src/data/engine.py` — SHADOW bootstrap, authorize, read, derive and revoke methods.
- `tests/data_quality/test_scope_readiness.py` — synthetic positive/negative proofs.
- `AXXEL_EDGE_DISCOVERY_MD/02_DATA/DATA_ENGINE.md` — contract and limits.
- `.axxel/master_architecture/13_STATE/AXXEL_STATE.json` — factual completion and gates.
- `.axxel/master_architecture/12_ROADMAP_BACKLOG/MASTER_ROADMAP.md` and
  `DETAILED_TASK_BACKLOG.md` — SHADOW milestone and pending gates.
- `reports/evidence/data_integrity_registry.json` — one append-only evidence entry.
- This report directory — before snapshots, manifests, machine test output and hashes.

The initial test failure is retained as a learning: keep denial reasons precise even
when both variants fail closed. Remaining risk is mistaking SHADOW authorization for
scientific certification; explicit status names, fixture-only root admission and
state booleans prevent that promotion.
