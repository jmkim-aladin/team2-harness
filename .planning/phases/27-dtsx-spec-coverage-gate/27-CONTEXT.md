# Phase 27 Context: DTSX Spec Coverage Gate

## Problem

Phase 26 readiness bundled local smoke, G1, equivalence, and local publish/readback evidence. However, readiness could still miss unresolved DTSX migration spec work if Script Task, loop, or unknown executable mappings remained in the generated spec.

## Constraint

No external DB, SQL Agent, FTP, SMB, HTTP, API, production, YouTrack, KB, push, or PR action.

## Target

Add an offline DTSX spec coverage report and make readiness require it. Manual-review DTSX steps must block readiness until they are resolved into Kotlin services, tasklets, partitioning, or deciders.
