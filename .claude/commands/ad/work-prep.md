# 작업 준비 (Work Prep)

YouTrack 티켓번호 또는 자유글 작업 설명을 입력받아, 로컬 Obsidian 운영 위키에 티켓 노트를 생성·갱신하고 업무를 시작할 컨텍스트를 묶어준다.

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

## 인보크 형태

```
/ad:work-prep DEV2-6127
/ad:work-prep 알라딘 앱 환불 정보 섹션 C2C 분기 누락 패치
/ad:work-prep                   # 아무 입력 없으면 무엇을 준비할지 질문
```

`ARGUMENTS`가 `^DEV2-\d+$` 패턴이면 **티켓 모드**, 그 외 텍스트면 **자유글 모드**로 분기한다.

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | YouTrack REST API 인증 |
| `$YOUTRACK_BASE_URL` | YouTrack 베이스 URL (기본: `https://aladincommunication.youtrack.cloud`) |
| `$TEAM2_HARNESS_PATH` | 팀 하네스 루트 (기본: `/Users/jm/Documents/workspace/team2`) |
| `$LOCAL_WIKI_PATH` | Obsidian vault 루트 (기본: `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`) |

## 참조 문서 (Source of Truth)

| 문서 | 경로 | 참조 항목 |
|------|------|-----------|
| 티켓 작성 가이드 | `$TEAM2_HARNESS_PATH/docs/sprint/ticket-guide.md` | 5W1H 규칙, 티켓 크기 |
| SP 가이드 | `$TEAM2_HARNESS_PATH/docs/sprint/story-point-guide.md` | SP 산정 |
| 위키 탐색 가이드 | `$TEAM2_HARNESS_PATH/docs/wiki-navigation-guide.md` | graph 우선, indexes, Graphify |
| 위키 문서 언어/제목 정책 | `$TEAM2_HARNESS_PATH/policies/wiki-document-language-and-title-policy.md` | H1/title 규칙 |
| Daily 운영 규칙 | `$LOCAL_WIKI_PATH/wiki/guides/daily-meeting-operating-rule.md` | daily 아젠다 등록 |
| 도메인 용어 링크 규칙 | `$LOCAL_WIKI_PATH/wiki/guides/domain-term-linking-rule.md` | canonical 용어 링크 |
| 서비스 카탈로그 | `$TEAM2_HARNESS_PATH/catalog/{서비스ID}.yaml` | 서비스 컨텍스트 |
| 팀원/오너 | `$TEAM2_HARNESS_PATH/policies/team-members.md` | 담당자 매핑 |

## 실행 흐름

### 1. 입력 분기

| 입력 | 분기 |
|------|------|
| `DEV2-XXXX` | 티켓 모드 → API로 본문 조회 |
| 자유글 | 자유글 모드 → 사용자 입력을 작업 설명으로 사용 |
| 없음 | "어떤 작업을 준비할까?" 질문 후 둘 중 하나 |

### 2. YouTrack 조회 (티켓 모드에서만)

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
AUTH="Authorization: Bearer $YOUTRACK_TOKEN"

# 본문 + 커스텀 필드 + 첨부 + 댓글
curl -s -H "$AUTH" \
  "$BASE/api/issues/DEV2-XXXX?fields=idReadable,summary,description,reporter(login,fullName),customFields(name,value(name,login,fullName,localizedName)),tags(name),attachments(name,url),comments(text,author(login,fullName),created)"
```

조회 실패(404/401) 시 사용자에게 알린다. **상태/필드/댓글을 변경하지 않는다** — 읽기 전용.

### 3. 서비스 추정 + 카탈로그 로드

- 티켓 모드: 제목 `[서비스명] ...` prefix, 본문, custom field 의 Project/Service를 분석
- 자유글 모드: 입력 텍스트의 서비스 키워드 (만권당/투비/naru/bazaar/aasm/shopping/storefront/caravan)로 추정
- 추정된 서비스가 있으면 `$TEAM2_HARNESS_PATH/catalog/{서비스}.yaml` 을 로드해 owner·repo·tech stack을 컨텍스트로 묶는다
- 서비스 추정 불가 시 사용자에게 질문

### 4. 위키 노트 경로 결정

| 모드 | 경로 |
|------|------|
| 티켓 모드 | `$LOCAL_WIKI_PATH/wiki/processes/tickets/in-progress/dev2-{NNNN}.md` (소문자, 4자리는 zero-pad 없이 그대로) |
| 자유글 모드 | 서비스 추정되면 `$LOCAL_WIKI_PATH/wiki/services/{서비스ID}/proposals/{kebab-slug}.md`, 추정 불가 시 `$LOCAL_WIKI_PATH/wiki/processes/tickets/backlog/{kebab-slug}.md` (티켓 발의 권장) |

기존 파일이 있으면 **읽어서** frontmatter `youtrack_synced_at`/`updated_at` 갱신만 하고, 본문은 보존한다. 사용자에게 "이미 있음 → 갱신" / "처음 생성" 인지 보고한다.

**기본 동작 (사용자 확인 없이 진행)**: 위키 노트 신규 생성·기존 노트 frontmatter 갱신·Daily 아젠다 추가는 미리보기를 출력한 뒤 바로 진행한다. 별도 확인 질문을 두지 않는다. 단, dev DB SQL 실행(§10)·브랜치 생성·YouTrack 변경은 여전히 사용자 확인 게이트를 유지한다.

### 5. 위키 노트 템플릿

#### 5.1 티켓 모드 frontmatter

```yaml
---
type: ticket
title: DEV2-{NNNN} {YouTrack 제목}
canonical_id: ticket:dev2-{nnnn}
status: canonical
updated_at: {YYYY-MM-DD}
ticket_id: DEV2-{NNNN}
ticket_status: in-progress    # auto-prep | in-progress | done | backlog
assignee: {jmkim 등 id}
service: {서비스ID}
sprint: {YYYY-MM}
type_yt: feature              # feature | task | bug
youtrack_state: {YouTrack 상태}
youtrack_synced_at: "{YYYY-MM-DD}"
sources:
  - youtrack: {BASE}/issue/DEV2-{NNNN}
  - harness: $TEAM2_HARNESS_PATH/catalog/{서비스}.yaml
  - repo: {서비스 repo 경로 (catalog에서)}
---
```

#### 5.2 자유글 모드 frontmatter

서비스 추정 시 `proposal` type, 추정 불가 시 `ticket` type (backlog status):

서비스 추정 → `wiki/services/{서비스ID}/proposals/{slug}.md`:
```yaml
---
type: proposal
title: {사람용 제목}
canonical_id: proposal:{서비스ID}/{kebab-slug}
status: draft
updated_at: {YYYY-MM-DD}
service_id: {서비스ID}
related_tickets: []          # 후속 티켓 발의 시 채움
---
```

서비스 추정 불가 → `wiki/processes/tickets/backlog/{slug}.md`:
```yaml
---
type: ticket
title: {사람용 제목}
canonical_id: ticket:backlog/{kebab-slug}
status: draft
updated_at: {YYYY-MM-DD}
ticket_id: TBD
ticket_status: backlog
assignee: jmkim
service: unknown
sprint: {YYYY-MM}
type_yt: task
---
```

(둘 다 후속 `/ad:ticket`으로 정식 발의 권장)

#### 5.3 본문 (두 모드 공통)

```markdown
# {제목}

## 한눈 요약 (TL;DR)

- 무엇을: {작업 한 줄}
- 왜: {배경/요구}
- 어디서: {대상 서비스/파일/모듈}

## 요청 요약

- 보고자: {fullName ({login}) — 자유글이면 본인}
- 담당자: {fullName ({login})}
- 유형/상태/우선순위/스프린트: {…}
- 발생 사실:
- 원 요청:
- 추가 회신/맥락:

## 연결 리소스

- 서비스 카탈로그: $TEAM2_HARNESS_PATH/catalog/{서비스}.yaml
- 서비스 repo: {경로}
- 관련 KB: {DEV2-A-XXX 후보 (검색 결과)}
- 관련 graph 노드: {운영 위키 graph/* 후보 — 가이드 §1}

## 가설 / 영향 분리

-

## 미확정 질문

-

## Actions

- [ ] {첫 단계}
- [ ] 담당자/오너 컨펌
- [ ] 검증 SQL 또는 회귀 테스트 항목 작성
- [ ] PR / 배포 라인업

## 완료 기록

- {YYYY-MM-DD}: 위키 노트 초안 생성 (`ad:work-prep`).
```

본문에 SP 원문, 운영 실데이터, 시크릿을 저장하지 않는다 (vault `AGENTS.md` 금지 항목).

### 6. 관련 KB 검색

```bash
# 제목/요약 키워드 2~3개 추출 후 OR 검색
curl -s -H "$AUTH" \
  "$BASE/api/articles?\$top=10&fields=id,idReadable,summary,parentArticle(summary)&query=project:DEV2 {키워드}"
```

매칭이 있으면 위키 노트 `연결 리소스 > 관련 KB`에 idReadable + 제목으로 적는다. 매칭이 없으면 그 줄을 비워둔다.

### 7. Daily 노트 아젠다 추가

`$LOCAL_WIKI_PATH/wiki/processes/daily/{오늘 YYYY-MM-DD}.md`를 열어 `## 오늘의 아젠다` 섹션에 한 줄 추가:

- 티켓 모드: `- [ ] [[wiki/processes/tickets/in-progress/dev2-{nnnn}|DEV2-{NNNN}]] — {제목 요약}`
- 자유글 모드: `- [ ] [[wiki/tasks/{YYYY-MM-DD}-{slug}|{제목}]]`

이미 동일 링크가 있으면 추가하지 않는다 (idempotent).
Daily 노트가 없으면 vault 템플릿 형식대로 생성한다 (`daily-meeting-operating-rule.md` 참조).

### 8. 브랜치 제안

- 티켓 모드: `feature/DEV2-{NNNN}` (커밋 메시지 prefix `[DEV2-{NNNN}]`)
- 자유글 모드: `feature/no-ticket-{kebab-slug}` (커밋 메시지 prefix `[NO-TICKET]`). 단, 자유글 모드는 **티켓 발의를 먼저** 권장 (`/ad:ticket`).

**자동 생성/체크아웃하지 않는다**. 사용자 확인 후에만 실행한다.

### 9. cmux 탭 이름 변경 (선택, cmux 안에서 실행 중일 때만)

현재 셸이 cmux 안에서 실행 중이면 작업 중인 서피스의 탭 이름을 티켓 식별자로 바꾼다. cmux 외부(일반 터미널/tmux/iTerm/VSCode 내장 등)에서는 **건드리지 않는다**.

감지:

```bash
if [ -n "${CMUX_WORKSPACE_ID:-}" ] && [ -n "${CMUX_SURFACE_ID:-}" ] && command -v cmux >/dev/null 2>&1; then
  CMUX_INSIDE=1
fi
```

리네이밍 (감지된 경우):

```bash
# 티켓 모드
cmux rename-tab --surface "$CMUX_SURFACE_ID" "DEV2-{NNNN} — {제목}"

# 자유글 모드
cmux rename-tab --surface "$CMUX_SURFACE_ID" "NO-TICKET — {제목}"
```

규칙:

- 제목은 한 줄로, 약 60자 이내로 자른다 (cmux 탭 폭 고려).
- 명령 실패(소켓 인증 실패, 서피스 ID 만료 등)는 경고만 출력하고 다른 단계를 막지 않는다.
- 워크스페이스 자체 이름(`workspace-action --action rename --title ...`)은 건드리지 않는다 — 사용자가 별도 작업 컨텍스트로 쓰고 있을 수 있다. 탭(=surface) 단위만 변경한다.
- 사용자 확인 없이 기본 진행. 변경 전후 이름을 출력에 명시한다.

### 10. 출력 형식

```
## 작업 준비 완료 — {제목}

| 항목 | 값 |
|------|-----|
| 모드 | 티켓 / 자유글 |
| 서비스 | {서비스ID} ({카탈로그 경로}) |
| 담당자 | {fullName ({login})} |
| 위키 노트 | $LOCAL_WIKI_PATH/wiki/processes/tickets/in-progress/dev2-{nnnn}.md (생성/갱신) |
| Daily 아젠다 | $LOCAL_WIKI_PATH/wiki/processes/daily/{YYYY-MM-DD}.md (추가/스킵) |
| cmux 탭 | DEV2-{NNNN} — {제목} (변경/스킵 — cmux 외부면 스킵) |
| 제안 브랜치 | feature/DEV2-{NNNN} (미생성) |
| 제안 커밋 prefix | [DEV2-{NNNN}] |

### 관련 KB 후보
- DEV2-A-… {제목}

### 다음 단계 (사용자 확인 후 실행)
1. 브랜치 생성: `git checkout -b feature/DEV2-{NNNN}` (해당 서비스 repo에서)
2. 위키 노트 보완: TL;DR / 영향 분리 / 검증 SQL 본문 작성
3. (자유글 모드인 경우) 티켓 발의: `/ad:ticket`
```

### 11. SQL 검증 (선택, 개발 DB 한정)

작업 준비 단계에서 영향 범위/스키마/데이터 분포를 확인할 SQL을 작성했고, 실측이 필요하면 **개발(dev) DB에 한해** 직접 조회해 검증해도 된다. 운영 데이터 추출 요청은 별도 절차([policies/data-request-policy.md](../../../policies/data-request-policy.md))를 따른다.

허용 범위:

- 대상: 카탈로그 `catalog/{서비스}.yaml`의 `dev`/`staging` DB. 운영(prod) DB는 금지.
- 작업: `SELECT`, `EXPLAIN`, `SHOW`, 스키마 조회. `INSERT/UPDATE/DELETE/DDL`은 사용자 명시 승인 없이는 금지.
- 접근 수단: CLI (`mssql-cli`, `psql`, `mysql` 등) 또는 사내 쿼리 도구. **DB 계열 MCP(postgres/mssql/mysql 등)는 사용하지 않는다** (글로벌 메모리 정책). 비-DB MCP는 무관.
- 자격증명: 본인 macOS Keychain에 등록한 항목을 `security find-generic-password -s {sm-...} -a $(whoami) -w`로 변수에 캡처해 사용하고, 사용 후 `unset`. 평문 파일·위키·하네스에 기록 금지. 상세: [policies/local-credentials-policy.md](../../../policies/local-credentials-policy.md). 운영 자격증명은 [policies/aws-secrets-convention.md](../../../policies/aws-secrets-convention.md) 절차로만 다루며 본 스킬에서는 사용하지 않는다.

실행 전 사용자에게 다음을 보여주고 확인을 받는다:

1. 대상 DB (서비스/환경 — 예: `max dev`)
2. 실행할 SQL 전문
3. 예상 결과 크기 (행 수 가늠)

결과 처리:

- 위키 노트 `가설 / 영향 분리` 또는 별도 `검증 SQL` 섹션에 **SQL 본문 + 결과 요약(스키마/카운트/대표 패턴)**만 남긴다.
- 운영 실데이터(개인정보·결제·이메일·전화·구매내역 등)는 **요약 수치/구조**로만 기록하고 row dump를 붙여 넣지 않는다.
- dev 환경이라도 실데이터 일부가 마스킹되지 않은 채 남아있을 수 있으므로 동일 원칙을 적용한다.

## 사용자 확인 게이트

**확인 없이 기본 진행하는 항목** (미리보기는 출력):

- 위키 노트 **신규 생성**: 경로 + frontmatter 미리보기를 출력한 뒤 바로 작성
- 위키 노트 **갱신**: frontmatter 변경 내역을 출력한 뒤 바로 작성 (본문은 보존)
- Daily 아젠다 **추가**: 추가할 한 줄을 출력한 뒤 바로 추가 (idempotent — 중복 시 스킵)
- **cmux 탭 이름 변경**: cmux 안에서 실행 중일 때만 (§9), 변경 전후 이름을 출력에 명시. 외부면 스킵

**확인 필수 항목**:

- **개발 DB SQL 실행**: 대상/SQL/예상 결과를 보여주고 확인 후 실행 (§11)
- 브랜치 생성, git 명령, YouTrack 변경: **하지 않는다** — 제안만

## 금지

- YouTrack 상태/필드/댓글 변경 (조회 전용)
- 브랜치 자동 생성/체크아웃
- 운영(prod) DB 직접 조회/변경 — 데이터 추출 요청 절차로 전환
- 개발 DB라도 사용자 사전 승인 없는 쓰기 쿼리(`INSERT/UPDATE/DELETE/DDL`)
- DB 계열 MCP 서버(postgres/mssql/mysql 등) 사용
- SP 원문/운영 실데이터/시크릿/개인정보를 위키 본문에 저장
- placeholder `/Users/user/...`를 실제 경로로 해석해 파일 생성 (반드시 `$LOCAL_WIKI_PATH` 사용)
- vault의 `<!-- GENERATED:START -->` ~ `<!-- GENERATED:END -->` 외부 영역을 자동 갱신

## 문서 위치 결정

작업 중 생성하는 노트·산출물은 `policies/knowledge-base-policy.md`의 결정 트리에 따라 즉시 위치를 결정한다. 매번 사용자에게 묻지 않는다.

- 정책/템플릿/카탈로그/스킬 → repo
- 전사·사내 공통 컨벤션·온보딩 → YouTrack KB
- 운영 데이터 추출 SQL/결과물 → data-requests-dev2 repo
- 특정 서비스 코드와만 의미 있는 매뉴얼 → 그 서비스 repo
- 그 외 (프로젝트 진행·운영·도메인·회의·일지·티켓 산출물·OKR) → Obsidian vault

## frontmatter 표준 (티켓 산출물)

```yaml
---
type: ticket
ticket_id: DEV2-XXXX
ticket_status: auto-prep | in-progress | done | backlog
assignee: jmkim
service: max
sprint: 2026-05
type_yt: feature | task | bug
---
```

상세: vault `wiki/guides/frontmatter-spec.md`.

## 사전 분석 (auto-prep) 활용

vault `wiki/processes/tickets/auto-prep/{DEV2-id}.md` (야간 자동 분석 산출물) 존재 시 본문을 시작점으로 정리한다. 사람 검토 후 in-progress로 이동.

ARGUMENTS: $ARGUMENTS
