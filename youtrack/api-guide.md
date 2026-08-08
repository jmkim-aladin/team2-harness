# YouTrack API 공통 가이드

`ad:*` 스킬이 YouTrack을 호출할 때의 공통 규약. 스킬 본문에는 그 스킬 고유의 쿼리만 남기고, 아래 공통부는 이 문서가 SoT다 (추출 근거: 2026-08-08 감사 — 환경변수 표 10곳·셋업 11곳·동일 호출 패턴 2~6곳 중복).

## 원칙

- **REST API(curl)만 사용한다. MCP 도구를 호출하지 않는다**
- 이슈/Task 생성, 상태·필드 변경, KB 생성·수정·삭제는 **사용자 확인 후** 실행 — 조회는 자유
- 응답의 개인정보·토큰은 출력에 남기지 않는다

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | REST API 인증 (본인 계정 토큰 — 아래 owner 규칙) |
| `$YOUTRACK_BASE_URL` | 베이스 URL (기본: `https://aladincommunication.youtrack.cloud`) |

## 셋업 (모든 curl 블록 공통)

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
YOUTRACK_TOKEN="${YOUTRACK_TOKEN:-$(python3 "${TEAM2_HARNESS_PATH:-$HOME/Documents/workspace/team2}/tools/cred.py" get youtrack-token)}"
AUTH="Authorization: Bearer $YOUTRACK_TOKEN"
```

토큰은 OS 금고(macOS Keychain / Windows Credential Manager)에 산다 — env는 폴백일 뿐, **settings.json·.env 등 평문 파일에 두지 않는다** ([local-credentials-policy.md](../policies/local-credentials-policy.md)).

스킬의 코드 블록에서 `$BASE`·`$AUTH`가 보이면 이 셋업을 전제한다.

## 토큰 owner 규칙 (쓰기 작업 전 필수)

YouTrack은 이슈 생성 시 reporter를 토큰 owner로 박고, 일반 권한으로는 변경할 수 없다. 다른 사람 토큰이면 모든 티켓이 그 명의로 등록된다.

```bash
curl -s -H "$AUTH" "$BASE/api/users/me?fields=login,fullName,email"
```

owner가 본인 계정과 다르면 **쓰기 작업을 중단**하고 본인 토큰 교체를 요청한다.

## 공통 호출 패턴

```bash
# 이슈 상세 (본문 + 커스텀 필드 + 태그 + 첨부 + 댓글)
curl -s -H "$AUTH" \
  "$BASE/api/issues/DEV2-XXXX?fields=idReadable,summary,description,reporter(login,fullName),customFields(name,value(name,login,fullName,localizedName)),tags(name),attachments(name,url),comments(text,author(login,fullName),created)"

# 이슈 검색 (query 문법은 YouTrack 표준)
curl -s -H "$AUTH" \
  "$BASE/api/issues?\$top=50&fields=idReadable,summary,customFields(name,value(name,login))&query={쿼리}"

# DEV2 프로젝트 internal id (이슈 생성 입력값)
curl -s -H "$AUTH" "$BASE/api/admin/projects?fields=id,shortName&query=DEV2"

# 이슈 생성 (사용자 확인 후)
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{ "project": {"id": "<internal id>"}, "summary": "...", "description": "..." }' \
  "$BASE/api/issues?fields=idReadable,summary"

# Assignee 갱신 (사용자 확인 후)
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{ "customFields": [{ "name": "Assignee", "$type": "SingleUserIssueCustomField", "value": {"login": "<login>"} }] }' \
  "$BASE/api/issues/{idReadable}?fields=idReadable,customFields(name,value(login))"

# KB 검색
curl -s -H "$AUTH" \
  "$BASE/api/articles?\$top=10&fields=id,idReadable,summary,parentArticle(summary)&query={키워드}"

# KB 상세
curl -s -H "$AUTH" "$BASE/api/articles/{idReadable}?fields=idReadable,summary,content,updated"
```

## Subtask 링크 생성

linkType id는 인스턴스 설정값이므로 하드코딩하지 않고 조회해서 쓴다.

```bash
# linkType 조회 (2026-08 스냅샷: Subtask = 161-3)
curl -s -H "$AUTH" "$BASE/api/issueLinkTypes?fields=id,name,sourceToTarget,targetToSource"

# 링크 추가 — suffix `s` = sourceToTarget(parent for). {parent}가 부모
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"idReadable":"{자식ID}"}' \
  "$BASE/api/issues/{parent}/links/{linkTypeId}s/issues"

# 링크 제거 — 자식의 internal id(`3-XXXXX`)가 필요
curl -s -X DELETE -H "$AUTH" \
  "$BASE/api/issues/{parent}/links/{linkTypeId}s/issues/{internal_id}"
```

## DEV2 KB 루트

- `DEV2-A-1` (Team): 팀 운영 (온보딩, 서버접속, 보안, 장애대응, OKR, 스프린트)
- `DEV2-A-21` (Shared): 공유 문서 (만권당, 투비 등 서비스별)
- `DEV2-A-22` (Onboarding): 온보딩
- `DEV2-A-108`: 😺만권당

## 상태 머신

전사 상태 플로우(ToBe→Closed)는 [ticket-guide.md](./ticket-guide.md)가 SoT.
