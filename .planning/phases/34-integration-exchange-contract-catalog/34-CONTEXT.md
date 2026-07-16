# Phase 34 Context: Integration Exchange Contract Catalog

## Trigger

User clarified that the migration is not always file-only: there are receiving flows and future contracts may be API/HTTP/FTP/non-file. The existing code already uses `Integration*` names in manifest/publish boundaries, but `FeedContractRegistry` and output specs could still read as file-only.

## Constraint

- No FTP, SMB, HTTP, API, SQL Server, production, YouTrack, KB, push, or PR action.
- G1 read-only evidence remains approval-needed.
- This phase may only add local contract modeling and reporting.

## Goal

Add a local exchange contract catalog so current file outputs and future non-file/inbound contracts can be represented by the same domain model.
