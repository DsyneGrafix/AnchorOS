# BOOT-0021 Standalone Package Manifest

Package: `AnchorOS-BOOT-0021-Security-Core-v0.1.1-standalone.zip`

Branch state: `feature/boot-0021-security-core`

Source baseline: DsyneGrafix/AnchorOS commit `d93b585` (`BOOT-0019`) with
the CP-001 Customer Onboarding Pipeline and BOOT-0021 Security Core changes.

## Package type

This is a **complete standalone AnchorOS repository snapshot**, not a patch or
overlay. It supersedes the incomplete v0.1 overlay package.

The ZIP contains one top-level directory:

```text
AnchorOS-BOOT-0021-Security-Core-v0.1.1/
```

That directory contains all 213 repository files required to run and verify
BOOT-0021, including:

- `core/boot_pipeline.py`, Module Manager, Lifecycle Manager, and Registry;
- all Platform Services, including Security Core;
- the complete Customer Onboarding Pipeline;
- all frameworks and startup modules;
- the complete AnchorIntel application;
- the S.P.A.T.I.A.L. engine and tests;
- both BOOT-0021 demonstrations and all tests;
- repository documentation and package instructions.

No pre-existing AnchorOS checkout is required.

For portable ZIP extraction, the historical BOOT-0018 release-notes filename
has been normalized from an embedded newline to a single-line em-dash-separated
name. Its contents are unchanged.

## Integrity inventory

`BOOT-0021-SHA256SUMS.txt` records SHA-256 digests for the other 212
repository files. The checksum inventory is the only file intentionally not
self-hashed.

After extraction:

```bash
cd AnchorOS-BOOT-0021-Security-Core-v0.1.1
sha256sum -c BOOT-0021-SHA256SUMS.txt
```

## Explicit prerequisite

Execution requires Python 3.11 or newer. Optional API dependencies are listed
in `requirements.txt`; the platform, Security Core, Customer Onboarding, and
S.P.A.T.I.A.L. test suites otherwise use repository-contained Python modules.

## Exclusions

The package contains no Git metadata, runtime database, customer data,
credentials, secrets, tokens, uploaded evidence, generated archive package,
backup, cache, bytecode, log, or temporary file.

No commit, push, merge, tag, release, or publication is included or implied.
