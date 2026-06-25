# Phase 45 Context - Legacy SQL Statement Risk Classification

## Why

Phase 43 and 44 made unresolved legacy SQL visible and blocked readiness on it. The next local improvement is to make unresolved SQL actionable without DB access by classifying each candidate into stored procedure, SELECT query, mutation SQL, or unknown/comment-truncated SQL.

## Constraint

This phase must not connect to SQL Server, SQL Agent, DTSX runtime, FTP, SMB, HTTP, API, production endpoint, YouTrack, KB, push, or PR. It only improves local analysis and generated reports.

## Expected Sample Shape

- SQL candidates: 46
- Stored procedure candidates: 34
- Unresolved candidates: 12
- SELECT candidates: 3
- Mutation candidates: 6
- Unknown candidates: 3
