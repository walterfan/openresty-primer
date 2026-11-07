---
title: Architecture Decision Records (ADR)
updated_time: '2026-10-09'
git_commit: 9edc900
updated_by: ai+trivial
source: []
owners:
  created_by: []
  updated_by:
  - codex
  responsible: []
ttl: null
review_status: pending
review_score: 0
reviewed_by: null
confidentiality: L1
summary: Architecture Decision Records (ADR)
tags:
  domain: []
  technology: []
  concepts: []
  audience: dev
  status: draft
---

# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records (ADRs) documenting significant architectural decisions made in this project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## ADR Format

Each ADR follows this structure:

- **Status**: Proposed, Accepted, Deprecated, or Superseded
- **Context**: The circumstances and constraints
- **Decision**: What was decided
- **Alternatives**: Other options considered
- **Consequences**: The results of the decision (positive, negative, neutral)

## How to Create an ADR

Use the `/PKB-adr` command:

```bash
/PKB-adr "Use PostgreSQL over MongoDB"
```

## ADR List

```{toctree}
:maxdepth: 1

template
```

## Index by Status

### Accepted

<!-- List accepted ADRs here -->

### Proposed

<!-- List proposed ADRs here -->

### Deprecated

<!-- List deprecated ADRs here -->

## References

- [ADR GitHub Organization](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
