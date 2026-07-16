# Phase 41 Context - G1 Import Approval Guard

## Situation

Phase 40 created the G1 approval packet, but `G1EvidenceImportCommandLineRunner` could still validate operator-supplied fragments without recording a matching approval decision.

This phase adds a local guard so real evidence import can be run in an approval-required mode.

## Boundary

The guard does not collect evidence and does not contact SQL Server, SQL Agent, FTP, SMB, HTTP, APIs, production paths, or partner endpoints. It only validates local JSON approval artifacts before local fragment import.

## Inputs

- G1 approval packet JSON
- G1 approval decision JSON
- operator-supplied G1 fragment directory

## Output

- import report with approval packet id, request id, and decision status
- no pack/validation report when approval is required but missing or invalid
