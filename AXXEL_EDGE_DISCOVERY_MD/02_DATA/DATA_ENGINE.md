# AXXEL Data Engine V1

Data Engine is the mandatory market-data boundary of AXXEL, implemented in `src/data/engine.py` and `quality.py`. Existing Experience Store, Discovery, probabilistic ML, economic simulations, evidence registry, memory and graph remain the scientific system. There is no second research system.

## Official flow

`SOURCE → RAW IMMUTABLE → NORMALIZE/BRONZE → VALIDATE → CLEAN/SILVER → QUALITY → FREEZE → RESEARCH DATASET/GOLD → Discovery/ML/economic backtest → costs/walk-forward/Skeptic`.

V1 accepts timezone-aware OHLCV Parquet with an explicit broker/instrument/point/timeframe/BAR_OPEN contract. M1 and M5 bars are supported; the reused feature/experience adapter is M1-only. Live MT5/MCP acquisition, CSV, naïve timestamps and ticks are not certified by this adapter. Their old publication commands are disabled before network access, rather than silently producing uncertified inputs. No broker connection was used for the pilot.

## Storage and reconstruction

- `data/engine/raw/DEV/<sha256>.parquet`: byte-for-byte immutable snapshot of the supplied bounded Parquet. Legacy extraction is explicitly an immutable *export*, not the original provider response.
- `data/engine/datasets/DE1-<recipe-hash>/bronze.parquet`: explicit numeric conversion, UTC normalization and source-row identity.
- `silver.parquet`: stable chronological ordering and exact-duplicate removal only. Price anomalies and conflicting records remain available, but can block the entire dataset.
- `findings.parquet`: source row, UTC timestamp, code, classification and explanation for every detected finding.
- `quality.json`: counts, coverage, score formula, limitations and status.
- `manifest.json`: final commit marker; source metadata, RAW and derived SHA256, schema, range, rows, transformation recipe, source-code hashes, dependency versions, frozen partition policy and provenance.
- `code/`: immutable snapshots of the engine, quality rules and feature/label implementation. Gold refuses a current implementation differing from its parent's frozen recipe. Python version is recorded alongside dependencies.
- `dev.parquet`, `experience_manifest.json`, `gold.json`: eligible M1 experience export, bound to the parent certificate and registered in the existing Experience Store index.

Temporary files are never discoverable as committed datasets. Publication uses exclusive hard-link creation after flushing, not overwriting. Existing files must match byte-for-byte. The recipe excludes wall-clock generation time; equal source bytes, metadata, code, dependencies and policy produce equal IDs. The logical hash is an Arrow IPC SHA256 with its Arrow version recorded; byte and logical hashes are deliberately separate. Changes require a new ID, never a rewritten experiment.

This is application-level immutability/integrity, not tamper-proof storage against the OS owner. A user able to rewrite source code or all certificates can bypass any Python library. Strong hostile-user isolation requires separate OS identities/ACLs or signed external custody; V1 does not claim that protection. Readers reject unknown certificates, mismatched hashes and paths outside the engine root.

## Scientific gates

The frozen existing partition calendar remains authoritative. V1 exposes DEV only. VALIDATION needs a separate ceremony and an implemented capability; V1 offers neither a Boolean bypass nor a validation loader. LOCKED_OOS cannot be read, including for checksum verification.

Partition membership is checked before payload access from Parquet footer ranges and again from observed timestamps. Sources with mixed rowgroups are rejected. The explicit legacy pilot mode reads only whole DEV rowgroups and records skipped groups. It relies on the local Parquet footer's correctness; it is not a sandbox for maliciously forged Parquet. SQL filtering is not a security boundary.

Normalization does not estimate anything from VALIDATION/OOS. No interpolation, backward fill, wick clipping, spread replacement or whole-history threshold fitting occurs. Gap alerts use declared intervals and fixed thresholds; broker calendar closures are not guessed. Missing historical broker-contract proof is a limitation, not inferred continuity. Features require contiguous past windows; future labels stop at the available partition boundary. MFE/MAE remain labels, not features.

## Findings and score

| Decision | V1 examples | Handling |
|---|---|---|
| FIX | Out-of-order records; byte-equivalent normalized duplicate observations | Stable sort/deduplicate silver; retain RAW and row lineage |
| KEEP_FLAGGED | Zero/wide spread, zero tick volume, stale runs, fixed 2% jump | Preserve values and flags |
| REVIEW | Gaps, off-grid times, broker/contract discontinuity | Preserve; block promotion to research until resolved under a new policy/version |
| REJECT | Nonfinite/nonpositive prices, invalid OHLC, negative spread/volume, conflicting duplicate timestamps, mixed symbols | Preserve evidence; deny research reads |

Score: `max(0, 100*(1-unique_flagged_rows/input_rows)-10)`; the ten-point limitation penalty reflects unverified broker history and execution-cost coverage. The score is descriptive, not an estimated probability. Critical gates override it. `REJECTED` and `EXPLORATORY_ONLY` cannot enter research. `USABLE_WITH_LIMITATIONS` may enter with explicit limitations; `RESEARCH_GRADE` is reserved and is not awarded by V1 while broker/calendar/cost provenance remains incomplete. Data quality never implies economic edge or permission to promote to MQL5.

## Commands

```powershell
python -m pip install -e ".[data-engine,ml]"
python -m pip install -r requirements-data-engine-lock.txt
python -m pytest tests -q
python scripts/run_data_engine.py --config config/data_engine_xauusd_m1_v1.json
```

For an independently supplied bounded source, create a new config with explicit source metadata and `legacy_dev_rowgroups: false`. `--build-experiences` publishes gold only if quality permits. The XAUUSD legacy pilot intentionally fails that additional gate. Do not downgrade the quality policy simply to make a command succeed.

DuckDB runs with two threads and a 1 GB query memory limit, explicit certified file paths and checked column projections; Parquet uses Zstandard and 100,000-row groups. No wildcard SQL or arbitrary SQL is exposed. Ingestion currently materializes the selected bounded dataset in memory and rejects selections above 2,000,000 rows before payload reads; larger imports must be provided in bounded source chunks. This is not an out-of-core whole-history processing claim.

## Historical evidence

### FOUNDATION_SCOPE_READINESS_V1 — SHADOW (ADR-FOUNDATION-001 approved)

The existing `DataEngine` owns an opt-in scope boundary; `src/data/scope.py` is its
pure metadata validator. There is no separate certification service, catalogue,
provider integration or capture worker. All new roots are synthetic fixtures.
`SC1-*` / `AXXEL-SCOPE-1` manifests are **SHADOW_ELIGIBLE**, not scientific certificates.
No production dataset has been enrolled or promoted.

The trusted host calls `configure_scope_shadow` once with already resident metadata,
a bound consumer/environment and a trusted clock. Only the host controls bootstrap;
consumer input must never be forwarded into this method. No lazy manifest/path
loader exists. A consumer supplies only the exact request fields to
`authorize_scope_shadow` / `read_scope_shadow`. Requests cannot supply paths,
manifests, clocks, fallback rules, cache keys or post-read filters. ALLOW is a
diagnostic result, not a reusable token: every read rechecks the complete parent
graph and current revocations/expiry before any artifact path, hash or cache access.

The closed manifest contract requires policy/schema versions, immutable ID/revision,
track, capabilities, instrument symbol/definition reference, half-open aware period,
fields, environment, purposes, consumers, partition, provenance references, validity,
revocation, parent ID/revision references and a bound physical artifact descriptor.
Capability/purpose/field semantics are explicit in `CAPABILITIES` and
`CAPABILITY_FIELDS`. Unknown versions, fields or capabilities are denied. Explicit
aware times are fixture/control metadata; this does not attest either legacy clock.

Track A admits only DEV research price fields; each research purpose is a separate
permission. It grants no XM spread, fees or fills. Track B uses FORWARD_EXECUTION
with PAPER/DEMO/LIVE context labels and explicitly separated quote, contract, fee
and fill permissions. These are labels on synthetic observations, never trading
authorization. Track B cannot relabel DEV, VALIDATION or LOCKED_OOS periods; absent
sealed-partition metadata disables B. All actual requests for VALIDATION/LOCKED_OOS
are denied. Cross-track/context joins are denied.

`derive_scope_shadow` registers only resident derivative metadata: capabilities,
fields, purposes, consumers, periods and validity are intersections of all parents;
instrument, track, partition and environment must agree. Provenance references
retain all parents. Union, concat, copy, rename and intermediate IDs cannot expand
rights. Features, labels, caches, experiences and model artifacts require parents.
No feature/label/model computation is implemented. New transformed field semantics
need explicit policy review; this minimal version does not invent field mappings.
`revoke_scope_shadow` immediately blocks future eligible uses through every ancestor
and clears the local cache. This is engine-local SHADOW state, not a durable global
revocation service. A fresh engine is default-deny until trusted bootstrap.

The physical reader only admits a whole pre-scoped Parquet fragment whose period
exactly equals the request. Its **entire** physical field/period descriptor must fit
all parent permissions before the full-file hash. Paths must match the fixed SC1
artifact location; resolved redirection is rejected before hashing. No RAW fallback
or row filtering exists. After authorization it verifies SHA256 before/after reading;
cache entries are copies bound to certificate/digest/projection and never bypass
reauthorization. Trusted admission must attest the descriptor against the bytes;
these gates do not themselves certify data quality or external provenance.

The trust boundary is the official Data Engine API, not a sandbox against arbitrary
Python code or an OS owner. Consumers must not receive host configuration/revocation
authority. Root manifests are trusted fixture input, not consumer assertions.
Production admission, durable revocation and consumer migration remain unimplemented.
The V1 APIs, DE1 IDs, snapshot recipe and original eligible DEV permissions retain
their original contract. Old manifests cannot acquire SC1 capabilities, and V1
readers reject SC1 IDs. SHADOW does not retrofit broad new rights into old contracts.

Verification and ALLOW/DENY matrix:
`reports/foundation_scope_shadow/2026-09-04/FOUNDATION_REPORT.md` and
`ALLOW_DENY_MATRIX.md`. DATA_ENGINE_CERTIFIED remains false; XM legacy and HistData
remain EXPLORATORY_ONLY; Control Tower remains blocked.

Existing ML falsification, reports, models and preregistrations are preserved. Uncertified V1 JSON and pre-engine Parquet cannot be re-read through official research APIs. The prior `ML_PARTITION_ACCESS_INCIDENT.json` remains relevant; the Data Engine pilot did not reopen holdout payloads and does not erase the earlier incident.

### TRACK_B_XM_FORWARD_CAPTURE_V1 — qualification running

The existing Data Engine now owns a bounded forward-capture worker in
`src/data/track_b_forward_capture.py`, configured by the frozen
`config/track_b_xm_forward_capture_v1.json`. It is limited to `XMGlobal-MT5 6`,
`GOLD`/`XAUUSD`, DEMO and read-only acquisition. It exposes no order method and
grants no fills, slippage, research, VALIDATION or LOCKED_OOS access.

For each request, the worker persists the exact NumPy array returned by
`MetaTrader5.copy_ticks_range` as `.npy` before creating the descriptor. It records
dtype, shape, strides, order and multiplicity, hashes all staged artifacts, writes a
manifest and final commit marker, then advances the checkpoint, then creates the
derived Parquet view without sorting or deduplicating. Errors, `None`, empty arrays,
retries, duplicates, reconnects, clock failures, backpressure and partial staging are
evidence, not silent repairs. A recovered interval is labelled
`RECOVERED_AFTER_GAP`. The request floor is always T0.

The official Python API exposes tick event times but no current server/terminal clock
or weekly quote/trade session-window functions in the installed version; these stay
`NOT_AVAILABLE`. The complete `symbol_info` response is preserved at its observed
time, while only a static contract projection controls specification intervals.
Metadata is never projected backward. Independent SNTP observations, receipt wall
time and monotonic time are recorded separately.

This is capture custody, not a claim of exhaustive tick delivery or a scientific
certificate. T0 was written immediately before the first authorized call capable of
returning symbol/quote data: `2026-09-04T19:18:39.974001Z`. Qualification is running;
the initial partial session does not count. G4 remains incomplete until five full
sessions, including weekly close/reopen and rollover, are retained and reviewed
without discarding bad sessions.

## Research basis

- [Pandera repository](https://github.com/unionai-oss/pandera) and [lazy validation](https://pandera.readthedocs.io/en/stable/lazy_validation.html): normalized dataframe contracts and aggregated failures; explicit transformations precede validation.
- [Great Expectations repository](https://github.com/great-expectations/great_expectations) and [Checkpoints](https://docs.greatexpectations.io/docs/reference/api/checkpoint_class/): validation results and actions are useful concepts, but a second framework/context is unnecessary for this local V1.
- [Microsoft Qlib health checker](https://github.com/microsoft/qlib/blob/main/scripts/check_data_health.py): missing OHLCV and abrupt-change diagnostics; stock-specific defaults are not adopted as gold-market truth.
- [Trading Strategy forward-fill](https://github.com/tradingstrategy-ai/trading-strategy/blob/master/tradingstrategy/utils/forward_fill.py): useful contrast for sparse market data; synthetic candles and wick repairs are deliberately not applied to XAUUSD news events.
- [Medallion architecture](https://docs.databricks.com/aws/en/lakehouse/medallion): separation of original, validated and research-ready data, implemented locally without Spark or cloud infrastructure.
- [DuckDB repository](https://github.com/duckdb/duckdb) and [Parquet overview](https://duckdb.org/docs/current/data/parquet/overview): local column projection and row-group pruning; performance features are not partition authorization.
