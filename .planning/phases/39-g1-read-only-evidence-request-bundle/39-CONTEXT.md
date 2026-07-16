# Phase 39 Context - G1 Read-only Evidence Request Bundle

## Objective

G1 승인 전에 운영자가 채워야 할 read-only evidence 수집 요청을 기계 검증 가능한 JSON bundle로 고정한다. 이 bundle은 수집 대상, 필수 fragment, read-only query template, import command, 금지 액션을 명시하며 DB/SQL Agent/FTP/SMB/HTTP/API/prod에는 접속하지 않는다.

## Current State

- Phase 38 b2b commit: `0a685ac`
- G1 evidence pack validator, template generator, fragment writer, directory importer는 이미 존재한다.
- 부족한 부분은 승인 요청 자체를 전달 가능한 artifact로 고정하는 것이다.

## Constraints

- No SQL Server, SQL Agent, FTP, SMB, HTTP, API, production, or partner endpoint connection.
- No DB write, SQL Agent disable/schedule change, DTSX execution, partner publish, or production file modification.
- Request bundle is an approval/operator handoff artifact only.
