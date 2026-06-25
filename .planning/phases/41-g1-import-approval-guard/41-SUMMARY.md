# Phase 41 Summary - G1 Import Approval Guard

## Result

`partner-integration-batch` now has an approval decision model and optional import guard. When `--partner.integration.g1-import.require-approval=true` is enabled, the importer requires both a G1 approval packet and a matching approval decision before writing the imported evidence pack.

Local b2b commit: `70d73f7`.

## Changes

- Added `G1ApprovalDecision` model.
- Extended `G1EvidenceImportReport` with approval packet id, request id, and decision status.
- Added `FAILED_APPROVAL_REQUIRED` import conclusion.
- Added approval guard checks to `G1EvidenceDirectoryImporter`.
- Added approval guard options to `G1EvidenceImportCommandLineRunner`.
- Added `docs/g1-evidence/approval-decision-template.json` as `PENDING`.
- Updated README, G1 import guide, migration ledger, and GSD planning ledger.

## Remaining Blocker

The committed approval decision template is intentionally not approved. G1 read-only evidence collection and an approved decision still require user/human approval.
