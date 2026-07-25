AnchorOS Security Documentation

Purpose

This directory contains the normative security standards,
architectural specifications, and supporting documentation
for the AnchorOS Security Core.

Document Hierarchy

SLS-001
Engineering Doctrine

↓

SLS-301
Security Architecture

↓

AOS-200
Security Core Architecture

↓

AOS-210 through AOS-270
Core Engine Specifications

Principles

Build with discipline.
Secure by design.
Verified by evidence.

Implementation Status

BOOT-0021 implements Security Core v0.1 as a bounded Platform Service under
`services/security_core/`. The implementation covers organization-scoped
identity metadata, configured roles and policies, default-DENY authorization,
hash-linked receipts, and deterministic replay. It is not an authentication
server, identity provider, token issuer, secrets manager, or enterprise IAM
system. See `services/security_core/README.md` for the executable boundary and
known limitations.
