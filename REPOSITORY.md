

# This repository is not a museum of every milestone. It is the authoritative implementation of AnchorOS today. Historical work is preserved through Git history and the archive, allowing the active repository to remain clean, understandable, and production-focused.



# AnchorOS Repository

**Repository:** AnchorOS
**Status:** Canonical Development Repository
**Version:** PROJECT-0001
**Maintainer:** Sirius Logic Systems

---

# Purpose

This repository is the canonical source for the AnchorOS platform.

It contains the current implementation of the platform, its services, applications, documentation, and engineering standards.

Historical milestone packages are retained only within the archive and are not considered part of the active platform.

---

# Repository Principles

1. The repository represents the **current state** of AnchorOS.
2. Historical releases are archived, not duplicated.
3. Documentation reflects the current platform unless explicitly marked historical.
4. Every component has a single authoritative location.
5. The Git history serves as the engineering record.

---

# Directory Structure

## apps/

End-user applications built on AnchorOS.

Examples:

- Mission Control
- AnchorIntel
- Customer Onboarding Demo

---

## core/

Platform runtime.

Contains shared execution framework, lifecycle management, module infrastructure, pipeline framework, and platform primitives.

---

## services/

Shared platform services.

Examples:

- Security Core
- Event Bus
- Configuration
- Health
- Audit
- Manifest

---

## pipelines/

Reusable deterministic workflow engines.

Example:

- Customer Onboarding Pipeline

---

## frameworks/

Industry-specific framework implementations.

Examples:

- AnchorFiber
- AnchorHealth
- AnchorGrid
- AnchorDefense
- AnchorStack

---

## docs/

Current platform documentation.

Suggested organization:

```
docs/
    architecture/
    platform/
    standards/
    guides/
```

Only current documentation belongs here.

---

## archive/

Historical engineering artifacts.

Examples:

```
archive/
    boot/
    releases/
    historical/
```

The archive preserves engineering history but is not considered part of the active platform.

---

## tests/

Automated verification and regression tests.

---

## assets/

Shared images, branding, icons, and supporting media.

---

# Documentation Rules

Current architecture documents remain under:

```
docs/
```

Historical milestone documents move to:

```
archive/
```

Release notes and verification reports belong with the archived release they describe.

---

# Source Code Rules

The active repository contains only the current implementation.

Obsolete implementations should be removed after their historical milestone has been archived.

---

# Git Rules

Do not commit:

- virtual environments
- local databases
- backups
- editor settings
- secrets

Refer to `.gitignore`.

---

# Engineering Workflow

1. Develop on feature branches.
2. Validate locally.
3. Merge into the canonical repository.
4. Tag significant milestones.
5. Archive completed milestone packages.

---

# Repository Goal

Maintain a clean, deterministic, production-ready AnchorOS platform that reflects the current state of engineering while preserving historical milestones through Git history and the archive.
