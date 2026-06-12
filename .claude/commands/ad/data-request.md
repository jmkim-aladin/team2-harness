# 운영 데이터 추출 요청 SQL 등록

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

YouTrack 데이터 추출 요청의 SQL과 산출물을 [`AladinCommunication/data-requests-dev2`](https://github.com/AladinCommunication/data-requests-dev2) 레포에 정책에 맞춰 등록한다.

## 정책 (Source of Truth)

작업 전 반드시 읽는다.

| 문서 | 경로 | 참조 항목 |
|---|---|---|
| 운영 데이터 추출 정책 | `policies/data-request-policy.md` | SSOT, 디렉터리 구조, 케이스 분기 |
| 데이터 추출 레포 README | [data-requests-dev2/README.md](https://github.com/AladinCommunication/data-requests-dev2/blob/main/README.md) | 브랜치/커밋/디렉터리 상세 |
| 가설 검증 순서 | `policies/hypothesis-verification-order.md` | 코드/dev DB → 잔여만 컨펌 |
| 로컬 자격증명 | `policies/local-credentials-policy.md` | dev DB 읽기 사전 동의 |

> SQL 작성 전 스키마·테이블 존재·예상 카운트는 dev DB 읽기 쿼리로 먼저 확인. 운영 의문은 코드/dev로 풀고, 잔여만 요청자에게 컨펌.

## 핵심 규칙 요약

- **브랜치**: `sprint/YYYY-MM` (당월). 없으면 `main`에서 분기 생성.
- **커밋 메시지**: `[DEV2-####] {요청 제목 또는 핵심 산출물 요약}`. 예: `[DEV2-6654] 합산 구매내역 통계 요청`. 기본값으로 `[DEV2-####] 요청 완료` 같은 범용 문구를 쓰지 않는다.
- **경로**:
  - 일반 단건: `요청부서/{부서}/DEV2-####/`
  - 만권당투비팀은 서비스별 하위 폴더(`만권당/`, `투비/`) 유지
  - 반복 요청: `요청부서/{부서}/{주제명}/` (`query.sql` 최신 유지 + `DEV2-####.md` 이력)
  - 시리즈 요청: `요청부서/{부서}/DEV2-####_{과제명}/` (티켓별 `.sql`)
- **파일**: 단건은 `query.sql` + `설명.md`, 또는 `DEV2-####.sql` 단일 파일.
- **요청부서**: `B2B솔루션팀`, `만권당투비팀`, `매장사업팀`, `음반굿즈팀`, `전략기획팀` 중 택일.

## 환경변수

| 변수 | 기본값 | 용도 |
|---|---|---|
| `$DATA_REQUESTS_DEV2_PATH` | `~/Documents/workspace/data-requests-dev2` | 레포 로컬 체크아웃 경로 |
| `$YOUTRACK_TOKEN` | — | 티켓 메타 조회용 (선택) |
| `$YOUTRACK_BASE_URL` | `https://aladincommunication.youtrack.cloud` | YouTrack 베이스 URL |

## 실행 지침

`/ad:data-request [DEV2-####] [요청부서] [설명]` 또는 인자 없이 호출 시 사용자에게 질문한다.

### 1단계: 입력 파악

다음을 확인한다. 누락된 항목은 사용자에게 묻는다.

- **티켓 ID** (`DEV2-####`)
- **요청부서** (위 5개 중 택일)
- **케이스 분류** (일반 단건 / 반복 요청 / 시리즈 요청)
  - 반복/시리즈면 추가로 주제명 또는 과제명
- **만권당투비팀**이면 서비스(`만권당` / `투비`)
- **SQL 본문 또는 SQL 파일 경로**
- **요청 설명 메타** (요청자, 요청일, 기준 기간, 주요 컬럼, 제약 사항)

티켓 메타가 필요하면 YouTrack API로 조회한다.

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$BASE/api/issues/DEV2-####?fields=idReadable,summary,description,customFields(name,value(name,login))"
```

### 2단계: 레포 준비

```bash
REPO="${DATA_REQUESTS_DEV2_PATH:-$HOME/Documents/workspace/data-requests-dev2}"

# 레포 없으면 사용자에게 클론 안내
if [ ! -d "$REPO/.git" ]; then
  echo "레포가 없습니다. 다음 명령으로 클론 후 다시 실행하세요:"
  echo "  git clone git@github.com:AladinCommunication/data-requests-dev2.git $REPO"
  exit 1
fi

cd "$REPO"
git fetch origin
git checkout main
git pull origin main

# 당월 스프린트 브랜치 확인/생성
SPRINT="sprint/$(date +%Y-%m)"
if git show-ref --verify --quiet "refs/heads/$SPRINT"; then
  git checkout "$SPRINT"
  git pull origin "$SPRINT" 2>/dev/null || true
else
  git checkout -b "$SPRINT"
  echo "스프린트 브랜치 $SPRINT 생성됨 — 첫 푸시 시 -u origin $SPRINT 필요"
fi
```

### 3단계: 파일 작성

케이스에 따라 경로 결정.

**일반 단건**:
```
요청부서/{부서}/DEV2-####/
  ├── query.sql
  └── 설명.md       (요청자, 요청일, 기준, 컬럼 매핑 등)
```

**만권당투비팀 단건**:
```
요청부서/만권당투비팀/{만권당|투비}/DEV2-####.sql    (단일 파일)
요청부서/만권당투비팀/{만권당|투비}/DEV2-####/        (폴더 + 설명)
```

**반복 요청**:
```
요청부서/{부서}/{주제명}/
  ├── query.sql           (최신)
  └── DEV2-####.md        (해당 회차 메모)
```

**시리즈 요청**:
```
요청부서/{부서}/DEV2-####_{과제명}/
  └── DEV2-####_{작업명}.sql
```

`설명.md`/`DEV2-####.md` 권장 형식:

```markdown
# DEV2-#### {제목}

- 티켓: https://aladincommunication.youtrack.cloud/issue/DEV2-####
- 요청자: {이름/팀}
- 요청일: {YYYY-MM-DD}
- 기준 기간: {YYYY-MM-DD ~ YYYY-MM-DD}
- DB: {DB명}
- 주요 컬럼: {핵심 컬럼 목록}
- 제약/주의: {NOLOCK, 인덱스, 파라미터 등}

## 실행 방법

{필요 시 파라미터 치환 방법}
```

**경로 표기 규칙** — 본 레포는 팀 공용이므로 작업자 로컬 환경 정보를 노출하지 않는다.

- ❌ 금지: 작업자 로컬 절대경로 (`/Users/jm/Documents/workspace/shopping/shop-db-script/...`, `~/Documents/workspace/...`)
- ❌ 금지: 다른 레포의 상대 경로 (`shop-db-script/databases/WebCatalog/Tables/Foo.sql`, `aladin-mall-migration/WebRelease/...`)
- ✓ 권장: **DB/스키마 식별자**로 표기 — `WebCatalog.dbo.Foo` (테이블), `WebCatalog.dbo.Foo_Get_SP` (SP), `Community.dbo.Bar` 등
- ✓ 운영 도구 URL은 그대로 (예: `https://www.aladin.co.kr/aaintraweb/...`)
- ✓ 외부 레포 식별이 꼭 필요하면 레포 루트 기준으로 단축: `shop-db-script` → `WebCatalog 스키마` / `aladin-mall-migration` → `AaIntraWeb 페이지` 식으로 의미 단위 표현

예시:

```diff
- 추적 경로:
- - `/Users/jm/Documents/workspace/shopping/aladin-mall-migration/WebRelease/AaIntraWeb/PageTracker/CustomerInBox.aspx.cs:52`
- - `shop-db-script/databases/WebCatalog/StoredProcedures/Customer_InBox_Timeline_V2.sql:195-256`
- - `shop-db-script/databases/WebCatalog/Tables/CustomerLoginHistory.sql`
+ 추적 경로:
+ - 운영 도구: `AaIntraWeb/PageTracker/CustomerInBox.aspx?QueryType=8` (https://www.aladin.co.kr/aaintraweb/...)
+ - SP: `WebCatalog.dbo.Customer_InBox_Timeline_V2` (QueryType=8 분기)
+ - 테이블: `WebCatalog.dbo.CustomerLoginHistory`
```

위키 노트(Obsidian vault `wiki/processes/tickets/`)와 작업자 로컬 메모에는 정확한 파일경로·라인번호를 남겨도 되지만, **data-requests-dev2 레포 산출물에는 DB 식별자만 기록한다**.

### 4단계: 커밋

```bash
cd "$REPO"
git add 요청부서/{부서}/DEV2-####/
git status
git diff --cached
```

사용자에게 diff 확인 받은 후:

```bash
git commit -m "[DEV2-####] {요청 제목 또는 핵심 산출물 요약}"
```

**커밋 메시지 예시**:
- `[DEV2-6654] 합산 구매내역 통계 요청`
- `[DEV2-6807] 앱푸시 발송 리스트 쿼리 작성`
- `[DEV2-1234] 회원 등급별 구매주기 통계 요청`

규칙:

- 티켓 제목이나 요청자가 보는 산출물명을 짧게 요약한다.
- `요청 완료`, `쿼리 작성`, `수정`처럼 단독으로 봤을 때 내용을 알 수 없는 범용 문구는 기본값으로 쓰지 않는다.
- 조건 보정/후속 수정 커밋은 `[DEV2-####] {무엇을 바꿨는지}`로 쓴다. 예: `[DEV2-6807] 조건 AND 교집합 정정 + 19세·본인인증 필터 추가`.

### 5단계: 푸시

사용자 확인 후 푸시한다. (CLAUDE.md 정책: 커밋/푸시 전 반드시 사용자 확인)

```bash
git push origin "$SPRINT"        # 기존 브랜치
git push -u origin "$SPRINT"     # 신규 브랜치 첫 푸시
```

### 6단계: 결과 안내

사용자에게 다음을 보고한다.

- 등록 경로: `요청부서/{부서}/...`
- 커밋 해시 및 메시지 (`[DEV2-####] {요청 제목 또는 핵심 산출물 요약}`)
- 브랜치 (`sprint/YYYY-MM`)
- 후속 작업 제안:
  - YouTrack 티켓 상태 업데이트 (사용자 확인 필요)
  - 요청자에게 결과 전달
  - 월말 `main` merge 시점 안내

## 금지 사항

- 하네스(`team2/docs/`)에 추출 SQL 신규 작성 — 정책 위반
- `main` 브랜치 직접 커밋 — 반드시 `sprint/YYYY-MM` 경유
- 커밋/푸시 전 사용자 확인 생략
- 티켓 ID 없는 커밋
- 정책에 없는 부서 폴더 신규 생성 (필요 시 사용자에게 확인)
- 설명.md / query.sql 주석에 작업자 로컬 절대경로(`/Users/jm/...`, `~/Documents/...`) 또는 외부 레포 상대경로(`shop-db-script/...`, `aladin-mall-migration/...`) 기록 — DB 식별자(`WebCatalog.dbo.Foo`)로만 표기

## 예외 처리

- **레포 미클론**: 클론 명령 안내 후 중단.
- **`sprint/YYYY-MM` 충돌**: `git pull` 후 재시도, 충돌 시 사용자에게 해결 요청.
- **티켓 ID 불명**: 사용자에게 질문. 추측 금지.
- **요청부서 불명**: 5개 후보 제시 후 사용자에게 선택받음.

ARGUMENTS: $ARGUMENTS
