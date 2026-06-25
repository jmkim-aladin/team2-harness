# Phase 32 Context: Manual Operation Tasklet Adapters

## Problem

Phases 29-31 implemented local services for all 17 DTSX manual-review worklist categories, but those services were not yet shaped as Spring Batch execution units.

## Target

Add a thin adapter layer that exposes the local manual operation services as Spring Batch `Tasklet` instances:

- copy
- transcode
- cleanup
- partitioned writer
- derived generation

The adapter must preserve the existing job style: successful operations return `RepeatStatus.FINISHED`; blocking operation statuses fail the step.

## Non-Goal

This does not attach the adapters to production job flows yet and does not execute DB/SP/SQL Agent/FTP/prod.
