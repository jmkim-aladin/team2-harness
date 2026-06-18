# 작업 준비 (Work Prep)

YouTrack 티켓번호 또는 자유글 작업 설명을 입력받아, 로컬 Obsidian 운영 위키에 티켓 노트를 생성·갱신하고 업무를 시작할 컨텍스트를 묶어준다.

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

## 인보크 형태

```
/ad:work-prep DEV2-6127
/ad:work-prep 알라딘 앱 환불 정보 섹션 C2C 분기 누락 패치
/ad:work-prep DEV2-6127 종료
/ad:work-prep                   # 아무 입력 없으면 무엇을 준비할지 질문
```

`ARGUMENTS`가 `^DEV2-\d+$` 패턴이면 **티켓 모드**, 그 외 텍스트면 **자유글 모드**로 분기한다.
`ARGUMENTS`에 DEV2 티켓번호와 `종료`, `완료`, `마감`, `닫`, `done`, `closed`, `fixed`, `resolved`가 함께 있으면 **티켓 종료 모드**로 분기한다.

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
| 티켓 작성 가이드 | `$TEAM2_HARNESS_PATH/docs/sprint/ticket-guide.md` | 5W1H 규칙, 티켓 크기, 위키 티켓 노트 작성 기준 |
| SP 가이드 | `$TEAM2_HARNESS_PATH/docs/sprint/story-point-guide.md` | SP 산정 |
| 위키 탐색 가이드 | `$TEAM2_HARNESS_PATH/docs/wiki-navigation-guide.md` | graph 우선, indexes, Graphify |
| 위키 문서 언어/제목 정책 | `$TEAM2_HARNESS_PATH/policies/wiki-document-language-and-title-policy.md` | H1/title 규칙 |
| Work Prep 노트 템플릿 | `$TEAM2_HARNESS_PATH/docs/sprint/work-prep-note-template.md` | frontmatter, 본문, 검증 SQL 상세 형식 |
| Daily 운영 규칙 | `$LOCAL_WIKI_PATH/wiki/guides/daily-meeting-operating-rule.md` | daily 아젠다 등록 |
| 도메인 용어 링크 규칙 | `$LOCAL_WIKI_PATH/wiki/guides/domain-term-linking-rule.md` | canonical 용어 링크 |
| 서비스 카탈로그 | `$TEAM2_HARNESS_PATH/catalog/{서비스ID}.yaml` | 서비스 컨텍스트 |
| 공통 서비스 정책 | `$TEAM2_HARNESS_PATH/policies/common-service-policy.md` | 공통 서비스 영향 확인 기준 |
| 공통 서비스 registry | `$TEAM2_HARNESS_PATH/catalog/common-services/registry.yaml` | 알라딘 인증/뉴빌링 등 공통 영향 경계 |
| 뉴빌링 프로파일 | `$TEAM2_HARNESS_PATH/catalog/common-services/new-billing.yaml` | 신규 빌링 API 경계 |
| 팀원/오너 | `$TEAM2_HARNESS_PATH/policies/team-members.md` | 담당자 매핑 |

## 검증 순서 원칙

[policies/hypothesis-verification-order.md](../../../policies/hypothesis-verification-order.md) 적용. 요지:

1. 코드 레벨 (§3.5) → 2. 데이터 레벨 (§11) → 3. 잔여 항목만 보고자/오너 컨펌
2. dev DB 읽기 쿼리는 사전 동의됨 — 즉시 실행
3. 위키 노트 `## 미확정 질문`에는 1·2로 풀리지 않은 항목만 남긴다

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
- 로그인/SSO/세션/권한/회원 식별/결제/청구/환불/정산/구독/공유 DB·SP·API·event/outbox 단서가 있으면 `$TEAM2_HARNESS_PATH/policies/common-service-policy.md` 와 `$TEAM2_HARNESS_PATH/catalog/common-services/registry.yaml` 을 함께 로드한다
- 신규 빌링, 결제, 정산, 구독, 빌링키 기능이면 `$TEAM2_HARNESS_PATH/catalog/common-services/new-billing.yaml` 을 로드하고, 뉴빌링 API 경유 여부와 미경유 사유를 `공통 서비스 영향`에 남긴다
- 공통 서비스 후보가 있으면 위키 노트에 `공통 서비스 영향` 섹션을 추가하고, 오너 확인 전에는 candidate/evidence로만 기록한다. owner-confirmed 전까지 confirmed/canonical/done으로 승격하지 않는다
- 서비스 추정 불가 시 사용자에게 질문

### 3.5 코드 레벨 진입점 분석 (자동)

서비스 카탈로그로 repo가 식별되면 **사용자 확인 없이** 코드 레벨 진입점·호출 SP·테이블을 탐색한다. 탐색 결과는 위키 노트 `비즈니스 로직`에는 판단으로, `기술 근거`에는 재탐색 가능한 짧은 식별자로 반영한다. 서비스 종류와 무관하게 같은 기조로 진행하며, 도구는 서비스에 맞게 선택한다.

탐색 우선순위 (도구는 서비스 환경에 따라 선택):

1. **콜그래프 DB 활용** — 서비스에 sqlite 콜그래프(graphify 등) 인덱스가 있으면 우선 사용. 예) shopping은 `/Users/jm/Documents/workspace/shopping/graphify/graph.db`:
   - aspx/엔드포인트 경로 단서: `fromAspx <path>` / `fromAlajax <name>`
   - SP 이름 단서: `whoCalls <sp>`
   - 영향 분석: `impact <file|sp>`
   - 다른 서비스도 동일한 콜그래프/심볼 인덱스가 있으면 같은 방식으로 적용. 키워드만 있을 땐 grep으로 후보 진입점을 먼저 식별한 뒤 콜그래프로 체인 확장.
2. **grep/심볼 검색 폴백** — 콜그래프 미구축 서비스 (Kotlin/Spring, Node, VB6 등):
   - repo 루트에서 `grep -rli "{도메인 키워드}" <코드 루트>` (한·영 동시. 예: "구매제한", "BuyBlock", "PartnerCid")
   - 진입점 후보 (`.aspx`/`.cs`/`.kt`/`.ts`/`.bas`/`.frm` 등) 5개 이하로 추림
   - IDE 심볼 인덱스(LSP, ctags, Sourcegraph 등)가 있으면 함께 사용
3. **테이블·SP·외부 호출 식별** — 진입점에서 호출되는 테이블/SP/HTTP 의존성을 추출하되, 본문에는 "무슨 정책/트리거/예외 판단에 필요한 근거인지"를 먼저 적는다. 콜그래프가 있으면 핵심 `reads_table`/`calls_sp` 엣지 3-5개만 인용하고, grep 폴백이면 파일·심볼·라인 링크만 남긴다.

탐색 결과가 비면 "후보 미식별" 항목으로 명시 (감추지 않는다). 키워드 후보를 노트에 적어 다음 사이클에서 다시 시도.

기록 밀도:

- 첫 50줄 안에 문제, 현재 판단, 해결 방향, 다음 행동이 모두 보여야 한다.
- `비즈니스 로직`은 트리거/정책/예외/운영 영향을 3-5개 bullet로 요약한다.
- `기술 근거`는 재탐색용 식별자만 남긴다. 파일 경로·SP·테이블 대량 나열, 호출부 전문, 콜그래프 출력 전문은 본문에 붙이지 않는다.
- 운영 서버에서 사람이 직접 확인해야 하는 조회 SQL은 `검증 SQL` 섹션에 전문을 남긴다. 단, 판단 요약·검증 결과 뒤에 배치해 첫 화면을 밀어내지 않는다.
- 전수검사 목록, raw evidence는 티켓 하위 근거 파일(`wiki/processes/tickets/dev2-{NNNN}/...`) 또는 promote 대상 분석/결정 노트로 분리하고, 티켓 본문에는 링크와 결론만 둔다.

### 4. 위키 노트 경로 결정

| 모드 | 경로 |
|------|------|
| 티켓 모드 | `$LOCAL_WIKI_PATH/wiki/processes/tickets/dev2-{NNNN}.md` (소문자, 4자리는 zero-pad 없이 그대로) |
| 자유글 모드 | 서비스 추정되면 `$LOCAL_WIKI_PATH/wiki/services/{서비스ID}/proposals/{kebab-slug}.md`, 추정 불가 시 `$LOCAL_WIKI_PATH/wiki/processes/tickets/{kebab-slug}.md` (티켓 발의 권장) |

기존 파일이 있으면 **읽어서** frontmatter `youtrack_synced_at`/`updated_at` 갱신만 하고, 본문은 보존한다. 사용자에게 "이미 있음 → 갱신" / "처음 생성" 인지 보고한다.

**기본 동작 (사용자 확인 없이 진행)**: 위키 노트 신규 생성·기존 노트 frontmatter 갱신·티켓 종료 반영·Daily 아젠다 추가는 미리보기를 출력한 뒤 바로 진행한다. 별도 확인 질문을 두지 않는다. 단, dev DB 쓰기 쿼리(§11)·브랜치 생성·YouTrack 변경은 여전히 사용자 확인 게이트를 유지한다.

### 5. 위키 노트 작성

상세 frontmatter와 본문 템플릿은 [Work Prep 노트 템플릿](../../../docs/sprint/work-prep-note-template.md)을 따른다.

필수 유지:

- 첫 50줄 안에 문제, 현재 판단, 해결 방향, 다음 행동이 보여야 한다.
- `status`는 문서 신뢰도, `ticket_status`는 작업 흐름, `decision_status`는 Hermes board 노출 조건으로 분리한다.
- 사용자 결정/승인/검토/blocked 항목이 남으면 `decision_status`를 `decision-needed | approval-needed | review-needed | blocked` 중 하나로 둔다.
- `비즈니스 로직`은 트리거/정책/예외/영향을 3-5개 bullet로 요약한다.
- `기술 근거`는 재탐색용 식별자만 남긴다. raw evidence는 티켓 하위 근거 파일이나 별도 분석 노트로 분리한다.
- 본문에 SP 원문, 운영 실데이터, 시크릿, 개인정보를 저장하지 않는다.

### 6. 관련 KB 검색

```bash
# 제목/요약 키워드 2~3개 추출 후 OR 검색
curl -s -H "$AUTH" \
  "$BASE/api/articles?\$top=10&fields=id,idReadable,summary,parentArticle(summary)&query=project:DEV2 {키워드}"
```

매칭이 있으면 위키 노트 `기술 근거 > 관련 KB`에 idReadable + 제목으로 적는다. 매칭이 없으면 그 줄을 비워둔다.

### 7. Daily 노트 아젠다 추가

`$LOCAL_WIKI_PATH/wiki/processes/daily/{오늘 YYYY-MM-DD}.md`를 열어 `## 오늘의 아젠다` 섹션에 한 줄 추가:

- 티켓 모드: `- [ ] [[dev2-{nnnn}|DEV2-{NNNN}]] — {제목 요약}` (Tolaria 호환: bare stem, path 금지)
- 자유글 모드: `- [ ] [[{YYYY-MM-DD}-{slug}|{제목}]]`

이미 동일 링크가 있으면 추가하지 않는다 (idempotent).
Daily 노트가 없으면 vault 템플릿 형식대로 생성한다 (`daily-meeting-operating-rule.md` 참조).

### 8. 브랜치 제안

- 티켓 모드: `feature/DEV2-{NNNN}` (커밋 메시지 prefix `[DEV2-{NNNN}]`)
- 자유글 모드: `feature/no-ticket-{kebab-slug}` (커밋 메시지 prefix `[NO-TICKET]`). 단, 자유글 모드는 **티켓 발의를 먼저** 권장 (`/ad:ticket`).

**자동 생성/체크아웃하지 않는다**. 사용자 확인 후에만 실행한다.

### 9. cmux/herdr 작업 라벨 변경 (선택, 감지된 환경에서만)

현재 셸이 cmux 안에서 실행 중이면 작업 중인 서피스의 탭 이름을 티켓번호만으로 바꾼다.
현재 셸이 herdr 안에서 실행 중이면 현재 tab/agent 이름은 티켓번호만, 현재 pane 이름은 티켓번호와 제목으로 바꾼다.
cmux/herdr 외부(일반 터미널/tmux/iTerm/VSCode 내장 등)에서는 **건드리지 않는다**.

감지:

```bash
CMUX_INSIDE=0
if [ -n "${CMUX_WORKSPACE_ID:-}" ] && [ -n "${CMUX_SURFACE_ID:-}" ] && command -v cmux >/dev/null 2>&1; then
  CMUX_INSIDE=1
fi

HERDR_INSIDE=0
if [ -n "${HERDR_ENV:-}" ] && [ -n "${HERDR_PANE_ID:-}" ] && command -v herdr >/dev/null 2>&1; then
  HERDR_INSIDE=1
fi
```

리네이밍 (감지된 경우):

```bash
# 티켓 모드
TAB_LABEL="DEV2-{NNNN}"
PANE_LABEL="DEV2-{NNNN} — {제목}"

# 자유글 모드라면 위 대신:
# TAB_LABEL="NO-TICKET"
# PANE_LABEL="NO-TICKET — {제목}"

# cmux 안이면 surface tab 이름 변경
if [ "$CMUX_INSIDE" -eq 1 ]; then
  cmux rename-tab --surface "$CMUX_SURFACE_ID" "$TAB_LABEL"
fi

# herdr 안이면 현재 tab + agent + pane 이름 변경
if [ "$HERDR_INSIDE" -eq 1 ]; then
  HERDR_TAB_ID="$(herdr pane get "$HERDR_PANE_ID" | jq -r '.result.pane.tab_id')"
  herdr tab rename "$HERDR_TAB_ID" "$TAB_LABEL"
  herdr agent rename "$HERDR_PANE_ID" "$TAB_LABEL"
  herdr pane rename "$HERDR_PANE_ID" "$PANE_LABEL"
fi
```

규칙:

- 티켓 모드는 tab/cmux surface에 `DEV2-{NNNN}`만 표시한다. 제목은 herdr pane label에만 둔다.
- 자유글 모드는 tab/cmux surface에 `NO-TICKET`만 표시하고, herdr pane label은 `NO-TICKET — {제목}`으로 둔다.
- 제목은 한 줄로, 약 60자 이내로 자른다 (pane 폭 고려).
- 명령 실패(소켓 인증 실패, 서피스·pane ID 만료 등)는 경고만 출력하고 다른 단계를 막지 않는다.
- cmux 워크스페이스 자체 이름(`workspace-action --action rename --title ...`)은 건드리지 않는다 — 사용자가 별도 작업 컨텍스트로 쓰고 있을 수 있다. 탭(=surface) 단위만 변경한다.
- herdr 워크스페이스 이름은 건드리지 않는다. 현재 tab/agent label은 티켓번호만, 현재 pane label은 제목 포함으로 변경한다.
- 사용자 확인 없이 기본 진행. 변경 전후 이름을 출력에 명시한다.

### 10. 출력 형식

```
## 작업 준비 완료 — {제목}

| 항목 | 값 |
|------|-----|
| 모드 | 티켓 / 자유글 |
| 서비스 | {서비스ID} ({카탈로그 경로}) |
| 담당자 | {fullName ({login})} |
| 위키 노트 | $LOCAL_WIKI_PATH/wiki/processes/tickets/dev2-{nnnn}.md (생성/갱신) |
| Daily 아젠다 | $LOCAL_WIKI_PATH/wiki/processes/daily/{YYYY-MM-DD}.md (추가/스킵) |
| cmux 탭 | DEV2-{NNNN} (변경/스킵 — cmux 외부면 스킵) |
| herdr tab | DEV2-{NNNN} (변경/스킵 — herdr 외부면 스킵) |
| herdr agent | DEV2-{NNNN} (변경/스킵 — herdr 외부면 스킵) |
| herdr pane | DEV2-{NNNN} — {제목} (변경/스킵 — herdr 외부면 스킵) |
| 제안 브랜치 | feature/DEV2-{NNNN} (미생성) |
| 제안 커밋 prefix | [DEV2-{NNNN}] |

### 관련 KB 후보
- DEV2-A-… {제목}

### 다음 단계 (사용자 확인 후 실행)
1. 브랜치 생성: `git checkout -b feature/DEV2-{NNNN}` (해당 서비스 repo에서)
2. 위키 노트 보완: 판단 요약 / 비즈니스 로직 / 검증 결과 정리
3. (자유글 모드인 경우) 티켓 발의: `/ad:ticket`
```

### 11. 검증 SQL 작성 + 실행 (개발 DB 한정)

§3.5에서 식별된 진입점·테이블·SP 기반으로 조회 SQL을 작성할 수 있다. 상세 형식과 기록 기준은 [Work Prep 노트 템플릿](../../../docs/sprint/work-prep-note-template.md) `검증 SQL 기준`을 따른다.

요약:

- `SELECT`/스키마 조회만 자동 허용한다. `INSERT/UPDATE/DELETE/DDL`은 별도 승인 전 금지.
- dev/staging 읽기 쿼리는 사전 동의 범위다. Keychain에서 credential을 읽고 사용 후 unset한다.
- 검증은 작은 모수와 짧은 기간으로 시작하고, 결과는 스키마/카운트/대표 패턴/판단만 노트에 남긴다.
- 운영(prod) 조회·추출은 직접 실행하지 않고 [data-request-policy.md](../../../policies/data-request-policy.md) 절차로 전환한다.
- 검증 SQL은 data-requests-dev2 등록 전에 먼저 티켓 노트나 티켓 하위 근거 파일에 저장한다.
- 만권당 CS 구독취소/환불에서 실제 사용 여부 확인이 필요하면 vault `wiki/services/max/analysis/subscription-usage-check-sql.md` 템플릿을 우선 사용한다.

### 12. 티켓 종료 모드 (로컬 위키 자동 반영)

사용자가 `DEV2-#### 종료`, `티켓 종료했어`, `완료 처리해줘`, `마감해줘`처럼 요청하거나 완료 사실을 보고하면 로컬 위키 티켓 노트를 자동 갱신한다. 이는 **Obsidian vault 기록 정리**이며 YouTrack 상태 변경이 아니다.

절차:

1. `$LOCAL_WIKI_PATH/wiki/processes/tickets/dev2-{nnnn}.md`를 찾는다. 없으면 티켓 모드 절차로 최소 노트를 만든 뒤 종료 반영한다.
2. 기존 노트를 읽고, 운영 raw row/개인정보/시크릿은 추가하지 않는다.
3. frontmatter를 갱신한다.
   - `ticket_status: done`
   - `decision_status: resolved` (열린 사용자 결정이 남아 있지 않을 때)
   - `updated_at: {오늘 YYYY-MM-DD}`
   - `status: canonical`은 결론·근거가 정리된 경우에만 유지/승격한다.
   - `youtrack_state`/`youtrack_synced_at`은 YouTrack API로 실제 조회한 경우에만 갱신한다. 사용자 보고만 있으면 완료 기록에 "사용자 보고 기준"이라고 남긴다.
4. 본문을 정리한다.
   - 판단 요약의 `다음 행동`을 `없음` 또는 `후속 후보`로 바꾼다.
   - `미확정 질문`은 `종료 시점 결정`으로 바꾸거나, 남은 항목을 `(후속 후보)`로 분리한다.
   - `Actions`에서 실제 완료된 항목만 `[x]`로 바꾸고, 별도 개발/개선은 `[ ] (후속 후보)`로 남긴다.
   - `완료 기록`에 `{오늘}: 사용자 안내/결과 전달 및 티켓 종료 반영. YouTrack API/KB/git 변경 없음.`을 추가한다.
5. `python3 tools/lint_vault.py --vault "$LOCAL_WIKI_PATH" --files "wiki/processes/tickets/dev2-{nnnn}.md"`를 실행해 검증한다.
6. 사용자에게 위키 파일, 변경 상태, lint 결과, 수행하지 않은 외부 변경(YouTrack/KB/git/DB)을 짧게 보고한다.

## 사용자 확인 게이트

**확인 없이 기본 진행하는 항목** (미리보기는 출력):

- 위키 노트 **신규 생성**: 경로 + frontmatter 미리보기를 출력한 뒤 바로 작성
- 위키 노트 **갱신**: frontmatter 변경 내역을 출력한 뒤 바로 작성 (본문은 보존)
- 위키 노트 **종료 반영**: 사용자가 티켓 종료/완료/마감/닫힘을 요청하거나 완료 사실을 보고하면 §12 기준으로 `ticket_status: done`과 종료 기록을 바로 반영
- Daily 아젠다 **추가**: 추가할 한 줄을 출력한 뒤 바로 추가 (idempotent — 중복 시 스킵)
- **cmux/herdr 작업 라벨 변경**: cmux/herdr 안에서 실행 중일 때만 (§9), 변경 전후 이름을 출력에 명시. 외부면 스킵

**확인 필수 항목**:

- **dev DB 쓰기 쿼리**(`INSERT/UPDATE/DELETE/DDL`): SQL 전문 + 영향 row + 롤백 계획 후 확인 (§11)
- 운영(prod) DB 조회/변경: 본 스킬에서 직접 수행 금지 — [data-request-policy.md](../../../policies/data-request-policy.md) 절차
- 브랜치 생성, git 명령, YouTrack 변경: **하지 않는다** — 제안만

> dev DB **읽기 쿼리**는 사전 동의되어 있어 확인 게이트 없이 실행 ([local-credentials-policy.md](../../../policies/local-credentials-policy.md) §"dev/staging DB 읽기 쿼리: 사전 동의").

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

## 사전 분석 (auto-prep) 활용

vault `wiki/processes/tickets/dev2-{id}.md` 중 frontmatter `ticket_status: auto-prep`(야간 자동 분석 산출물) 존재 시 본문을 시작점으로 정리한다.

상태는 **두 축을 분리**해서 다룬다 (vault `wiki/guides/frontmatter-spec.md` 참조):

- `status` (문서 신뢰도): 야간 산출물은 미검토 기계 생성이므로 `status: draft`로 들어온다. work-prep로 사람이 검토·분석을 끝내면 `status: canonical`로 승격한다 — **이것이 "분석 완료" 신호**다.
- `ticket_status` (작업 워크플로): YouTrack 작업 라이프사이클에 정렬되는 축. 작업을 시작하면 `in-progress`로 갱신한다. 분석 완료 신호로는 쓰지 않는다.

ARGUMENTS: $ARGUMENTS
