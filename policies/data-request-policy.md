# 운영 데이터 추출 요청 관리 정책

## 목적

YouTrack으로 접수되는 운영 데이터 추출 요청의 SQL과 산출물을 **별도 레포에서 관리**한다. 팀 하네스(`team2`)는 정책과 스킬만 보관하고, 실제 추출 SQL/산출물은 [`AladinCommunication/data-requests-dev2`](https://github.com/AladinCommunication/data-requests-dev2)에 둔다.

## SSOT

| 대상 | 저장소 |
|---|---|
| 추출 SQL, 요청별 산출물, 요청 이력 메모 | **`AladinCommunication/data-requests-dev2`** |
| 데이터 추출 도메인 지식 (테이블 인벤토리, 도메인 매핑, 조인 패턴, 함정 테이블) | **로컬 위키 `team2/wiki/`** |
| 데이터 추출 정책, 운영 가이드, 스킬 | **팀 하네스 `team2`** |

운영 데이터 추출 SQL을 하네스(`team2/docs/`)나 서비스 레포에 새로 만들지 않는다. 단, 도메인 지식 정리(예: 어떤 테이블이 어떤 의미인지)는 로컬 위키 인벤토리에 남기고, 실제 추출 쿼리는 data-requests-dev2 레포의 티켓 폴더에 둔다.

## 레포 규칙 (data-requests-dev2)

요약 — 상세는 레포 [README.md](https://github.com/AladinCommunication/data-requests-dev2/blob/main/README.md) 참조.

### 브랜치

- `main` — 스프린트 종료 시 merge되는 안정 브랜치
- `sprint/YYYY-MM` — 월별 스프린트 브랜치, 해당 월 모든 요청 작업

### 커밋 메시지

```
[DEV2-티켓번호] 커밋 설명
```

- 마지막 커밋에 `요청 완료` 표기 권장 (예: `[DEV2-5749] 요청 완료`)

### 디렉터리 구조

```
요청부서/{요청부서명}/{티켓번호 또는 주제 폴더}/
```

3가지 케이스:

| 케이스 | 구조 | 예시 |
|---|---|---|
| 일반 단건 요청 | `요청부서/{부서}/DEV2-####/{query.sql, 설명.md}` | `요청부서/B2B솔루션팀/DEV2-1234/` |
| 반복 요청 (동일/유사 쿼리 주기적) | `요청부서/{부서}/{주제명}/{query.sql, DEV2-####.md, ...}` | `요청부서/B2B솔루션팀/월별매출추출/` |
| 시리즈 요청 (한 과제 다중 티켓) | `요청부서/{부서}/DEV2-####_{과제명}/DEV2-####_{작업}.sql` | `요청부서/B2B솔루션팀/DEV2-1234_회원분석/` |

### 요청부서 명칭

현재 사용 중인 부서 폴더: `B2B솔루션팀`, `만권당투비팀`, `매장사업팀`, `음반굿즈팀`, `전략기획팀`.

만권당투비팀은 서비스별 하위 폴더(`만권당/`, `투비/`)를 유지한다.

## 작업 흐름

1. YouTrack 데이터 추출 티켓 접수 → 5W1H 정리
2. `data-requests-dev2` 레포에서 당월 `sprint/YYYY-MM` 브랜치 체크아웃 (없으면 생성)
3. 요청부서/주제에 맞는 디렉터리에 SQL과 설명 파일 작성
4. `[DEV2-####] {설명}` 커밋
5. 요청자에게 결과 전달 후 마지막 커밋에 `요청 완료` 표기
6. 월말 스프린트 종료 시점에 `main` merge

## 로컬 체크아웃

기본 경로: `~/Documents/workspace/data-requests-dev2` (team2 하네스 sibling).

환경변수 `$DATA_REQUESTS_DEV2_PATH`로 다른 경로 사용 가능.

## 스킬

`/ad:data-request` — 본 정책에 맞춰 SQL을 레포에 등록한다. 브랜치/디렉터리/커밋 규칙을 자동 적용한다.

## 예외

- 데이터 추출과 무관한 일반 분석 SQL, 일회성 디버깅 SQL은 본 정책 대상이 아니다.
- 도메인 지식 인벤토리는 로컬 위키 `team2/wiki/inventory/`에 두고, 추출 쿼리만 data-requests-dev2에 둔다.
- 본 정책 시행 이전에 하네스 `docs/`에 작성된 추출 SQL은 그대로 두고, 후속 이관은 별도 작업으로 처리한다.
