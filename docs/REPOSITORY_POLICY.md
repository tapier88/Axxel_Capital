# Repository publication and exclusions

| Category | Classification | Publication |
|---|---|---|
| src, scripts, tests, safe config | MUST_COMMIT | Current implementation and frozen tests/config; no activation changes |
| canonical master, AGENTS, executive docs | MUST_COMMIT | Current views reconciled; dated decisions preserved |
| safe scientific reports/manifests/preregistrations | SHOULD_COMMIT | Reviewed text/aggregate JSON with original bytes and hashes |
| historical state, semantic/long-term summaries | SHOULD_COMMIT | Documentary test dependencies; not current permissions |
| local MCP/Codex settings, credentials | SENSITIVE | Never publish; values not printed |
| V1/V2 operational dossiers, browser/host logs | LOCAL_ONLY | Preserve originals locally; safe status summary in docs |
| RAW, historical payloads, ticks, holdouts | LARGE_DATA / LOCAL_ONLY | Never read for publication, upload or hash holdouts |
| models, predictions, runtime stores | GENERATED / LOCAL_ONLY | Excluded; no model promotion |
| ZIP exports | GENERATED | Canonical source published; ZIP derived locally, public hash/manifest only |
| caches, binaries, temporary files | IGNORE | No Git tracking |

Initial metadata inventory: 3712 files / 1324210535 bytes. 14 files exceed 10 MiB,
4 exceed 50 MiB, all excluded data payloads. No LFS needed or activated. Exact sizes
and category reasons appear in LARGE_FILES.json; inventory used filesystem metadata,
not payload reads. The initial inventory precedes audit artifacts generated here.

Known credentials were found in local connection settings. Candidate content was
compared in memory against those values: zero matches. Pattern scans check token,
private-key, credential/account literals and personal paths without printing matches.
A clean scan means no known/detected patterns, not proof against all possible secrets.
Files with private paths remain local rather than modifying historical evidence.

Git attribute '* -text' preserves original bytes/line endings for scientific hashes.
Use a preparation branch; retain the remote initial commit; never force-push main.
Do not use git add -f on private evidence. Review the exact staged file inventory.

A public clone contains synthetic test code and safe historical aggregate reports;
raw-data experiments cannot be rerun from GitHub and are not authorized. Documentary
hash references to excluded local evidence are deliberately retained and labelled in
EVIDENCE_AVAILABILITY.md. They are not proof that the private bytes are publicly present.
