# FOUNDATION_SCOPE_READINESS_V1 — ALLOW / DENY matrix

Mode: **SHADOW, synthetic fixtures only**. An ALLOW here proves policy behavior; it
does not certify a provider, dataset, clock, calendar, quality result or execution.

| Request / operation | Result | Enforced before |
|---|---:|---|
| Exact SC1 version, capability, purpose, consumer, instrument, environment, partition, physical period and certified fields; active finite ancestry | ALLOW | Then fixed path, hash and payload; cache still reauthorizes |
| Unknown capability or manifest version | DENY | path / hash / payload / cache |
| Capability absent from certificate/any parent | DENY | path / hash / payload / cache |
| Missing, unknown or noncanonical request field | DENY | path / hash / payload / cache |
| Requested field absent from certificate/parent/artifact or invalid for capability | DENY | path / hash / payload / cache |
| Interval outside scope; narrower interval requiring post-read filtering | DENY | path / hash / payload / cache |
| Wrong symbol or instrument-definition ID | DENY | path / hash / payload / cache |
| Wrong environment, purpose or consumer | DENY | path / hash / payload / cache |
| VALIDATION, LOCKED_OOS, RAW or mismatched partition | DENY | path / hash / payload / cache |
| Revoked, expired or not-yet-valid certificate/parent | DENY | path / hash / payload / cache |
| Unknown/legacy certificate, bad parent revision, cycle or depth violation | DENY | path / hash / payload / cache |
| Cache identifier/manifest/path/filter/fallback supplied by consumer | DENY | all cache and artifact access |
| Missing, changed or redirected artifact | DENY | before payload; no fallback |
| Union/concat/copy/rename/select/cache/features/labels/experiences/model | ALLOW only at parent intersection | metadata-only registration; no transform executes |
| Derivative widens any capability/field/purpose/consumer/period/validity | DENY | derivative admission |
| Cross-track, cross-environment, cross-instrument or cross-partition join | DENY | derivative admission |
| Parent revoked after a descendant was cached | DENY descendant | cache lookup/use |
| Track A asks for XM spread/fees/fills/slippage | DENY | path / hash / payload / cache |
| Track B asks for research/Discovery/features/labels/ML/walk-forward/backtest | DENY | path / hash / payload / cache |
| Track B attempts to relabel any existing frozen historical partition | DENY | manifest admission |
| XM legacy or HistData EXPLORATORY_ONLY manifest | DENY | shadow admission; source remains unchanged |
| SC1 ID passed to V1 reader | DENY | V1 manifest/path access |

Test mapping is in `tests/data_quality/test_scope_readiness.py`; machine results are
`relevant_tests.xml` (134 passed) and `full_suite.xml` (253 passed). The preserved
initial failure demonstrates that an integrity denial was originally overgeneralized;
the final code retains the precise integrity reason and passes the full suite.
