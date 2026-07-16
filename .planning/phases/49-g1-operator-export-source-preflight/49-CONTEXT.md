# Phase 49 문맥: G1 operator export source preflight

## 배경

Phase 48까지 approval decision과 approval-guarded import는 가능해졌다. 하지만 현재 workspace에는 실제 operator `READ_ONLY_EXPORT` fragment가 없고, template 또는 local repo 후보 fragment만 있다.

실제 운영 fragment 경로가 들어왔을 때 곧바로 import하면 template placeholder나 local 후보를 운영 증거처럼 착각할 수 있다. import 전에 source-root 자체를 판정하는 preflight가 필요하다.

## 목표

operator source-root가 아래 조건을 만족하는지 import 전에 검사한다.

- 필수 fragment 7개가 모두 존재한다.
- `pack-metadata.json`의 `sourceType`이 `READ_ONLY_EXPORT`다.
- fragment 내용에 `TODO_` placeholder가 남아 있지 않다.
- `LOCAL_REPO_CANDIDATE`나 sample/template은 운영 증거로 들어오지 않는다.

## 경계

이 단계는 로컬 파일만 읽는다. SQL Server, SQL Agent, DTSX 실행, FTP, SMB, HTTP, API, 운영 endpoint, partner endpoint에 접속하지 않는다.
