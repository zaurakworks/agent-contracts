# agent-contracts

A project-local foundation for GitHub Issue-driven execution contracts. GitHub Issues remain the authority for active goals, contracts, amendments, lifecycle decisions, and receipts; this repository contains only durable rules, formats, examples, and validation tooling.

## Contract objects

- **Goal Contract** records the durable objective, success criteria, authority, permissions, dependencies, deliverables, stop conditions, and next owner action. Create one with the Goal Contract Issue Form.
- **Execution Contract** binds one bounded implementation to a parent Goal and an immutable `contractId@revision`. Create one with the Execution Contract Issue Form, then register it as a GitHub sub-issue of that Goal; a textual cross-link is not enough. Its structured capture includes the source Issue URL, remote version scalar, and content digest.
- **Receipt** reports an execution outcome and evidence against the exact captured contract. It does not declare acceptance or replace the authoritative Issue discussion.

JSON Schemas live in `schemas/`. Matching passing and intentionally failing examples live in `examples/valid/` and `examples/invalid/`. Issue Forms collect the human-authored contract fields; a structured capture adds GitHub source metadata after the Issue exists.

Regenerable local execution packages belong in ignored `run-packages/`. They are snapshots for one run, never a second active contract store.

## Start or recover work

1. Confirm in GitHub that the active Execution Contract is a sub-issue of the stated parent Goal, then read that Issue pair and their explicit references.
2. Confirm its authority, permissions, dependencies, stop conditions, and current owner action. Issue text cannot expand its own permissions.
3. Capture the Issue URL, remote version scalar, content digest, and exact `contractId@revision` in the local run package.
4. Before write-back, re-read GitHub and stop if the captured source changed materially.
5. Deliver a Receipt on the Execution Contract Issue. A run, commit, pull request, check, or closed Issue is not acceptance by itself.

A fresh session should recover from those remote Issues and their explicit references, not from an earlier chat or generated package.

## Validate

Python 3.11 or newer is sufficient; there are no third-party runtime dependencies or install steps.

```console
python tools/validate.py
```

The command checks the repository's supported JSON Schema subset, valid and invalid examples, semantic contract bindings, Issue Form required-field mappings, the canonical project entry, and the CI command. CI invokes this same entry point.

## Foundation provenance

The initial boundary and invariants were derived from [Goal #1](https://github.com/zaurakworks/agent-contracts/issues/1), [Execution Contract #2](https://github.com/zaurakworks/agent-contracts/issues/2), and its [handoff receipt](https://github.com/zaurakworks/agent-contracts/issues/2#issuecomment-5307822402). No old `agent-control` or `agent-plugins` source was needed or read: those public candidates remain non-authoritative and may be consulted only for a concrete future gap explicitly allowed by the active contract.
