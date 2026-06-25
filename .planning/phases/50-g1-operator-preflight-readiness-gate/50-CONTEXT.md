# Phase 50 문맥: G1 operator preflight readiness gate

## 배경

Phase 49에서 operator source-root preflight를 추가했다. 그러나 readiness가 이 report를 필수 gate로 요구하지 않으면, preflight가 실패했는데도 G1 import approval이나 validation report만 보고 readiness가 앞으로 진행될 위험이 있다.

## 목표

readiness bundle에 `G1_OPERATOR_PREFLIGHT` gate를 추가해, 실제 operator `READ_ONLY_EXPORT` fragment가 preflight를 통과하기 전까지 readiness가 계속 `BLOCKED`로 남게 한다.

## 경계

이 단계는 기존 report JSON을 읽고 readiness summary를 생성한다. SQL Server, SQL Agent, DTSX 실행, FTP, SMB, HTTP, API, 운영 endpoint, partner endpoint에 접속하지 않는다.
