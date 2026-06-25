# Phase 41 Plan - G1 Import Approval Guard

## Goal

Prevent G1 evidence import from becoming accepted proof when approval is required but no matching approval decision exists.

## Steps

1. Add RED tests for approval-required import without decision.
2. Add RED tests for approved import report metadata.
3. Add `G1ApprovalDecision` model.
4. Extend import report with approval packet id, request id, and decision status.
5. Add importer guard checks for required approval.
6. Add command runner options:
   - `--partner.integration.g1-import.require-approval=true`
   - `--partner.integration.g1-import.approval-packet=...`
   - `--partner.integration.g1-import.approval-decision=...`
7. Add `approval-decision-template.json` as `PENDING`.
8. Update README, G1 import guide, migration ledger, and GSD planning ledger.
9. Run focused tests, G1 focused suite, and full tests.

## Acceptance

- Missing approval decision fails before output pack write.
- Matching approved decision allows import and records approval metadata.
- `PENDING` template is not accepted by guard.
- Existing non-guarded local import remains backward compatible.
