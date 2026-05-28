# 신규 노트 작성 (vault write-time AI 분류)

새 vault 노트 작성 시 type·위치·frontmatter·llm-hint를 자동 결정하고 lint-pass 상태로 생성한다.

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

## 사용법

```
/ad:new-note {제목 또는 키워드 또는 자유 묘사}
/ad:new-note 멀티캠퍼스 4월 데이터 추출 결과    # → processes/tickets/{slug}.md 추정
/ad:new-note 5월 4주차 회의록 storefront 멀티테넌시  # → processes/meetings/2026-05-27-storefront-multi-tenancy.md
/ad:new-note tobe 주문 환불 도메인 분석            # → services/tobe/domains/order-refund.md
/ad:new-note 김정민 6월 capacity                  # → processes/capacity/2026-06-kimjeongmin.md
```

자연어 입력 → AI가 분류 트리 적용 → 사용자 confirm → 생성.

## 결정 트리 (자동 적용)

vault `wiki/guides/document-placement.md` 트리 기준.

| 입력 신호 | type | 위치 |
|---|---|---|
| `DEV2-NNNN` 패턴 | ticket | `wiki/processes/tickets/dev2-NNNN.md` (상태는 frontmatter `ticket_status`) |
| "회의록", "회의", 날짜 + 주제 | meeting | `wiki/processes/meetings/YYYY-MM-DD-{slug}.md` |
| "daily", "일지", 오늘 | daily | `wiki/processes/daily/YYYY-MM-DD.md` |
| "주간보고", "주간업무", NW | weekly-report | `wiki/processes/weekly/YYYY-MM-NW-{user}.md` |
| "OKR", 분기 | okr | `wiki/processes/okr/YYYY-q[1-4]{-user}.md` |
| "장애", "incident", "postmortem" | incident | `wiki/processes/incidents/{slug}.md` |
| "capacity", "가용", 월 | capacity-plan | `wiki/processes/capacity/YYYY-MM{-user}.md` |
| 서비스명 + "도메인" | (domain note, in services/{svc}/domains/) | `wiki/services/{svc}/domains/{slug}.md` |
| 서비스명 + "분석", "audit", "gap" | analysis | `wiki/services/{svc}/analysis/{slug}.md` |
| 서비스명 + "결정", "ADR", "변경 결정" | decision | `wiki/services/{svc}/decisions/{slug}.md` |
| 서비스명 + "개선", "제안", "신청" | proposal | `wiki/services/{svc}/proposals/{slug}.md` |
| "프로젝트" + 다중 서비스 | project | `wiki/projects/{name}/{slug}.md` |
| 용어 정의 | glossary | `wiki/glossary/{term}.md` |
| 위 어디에도 안 맞음 | (사용자 확인) | (대화 후 결정) |

판단 모호 = 사용자에게 확인.

## frontmatter 자동 채움 (type별)

type 결정 후 `wiki/guides/frontmatter-spec.md` 기준 필수 필드 자동 채움.

기본 매핑:
- ticket: `ticket_id`(입력에서 추출), `ticket_status: in-progress`(기본), `assignee`(YOUTRACK_USER 또는 김정민 jmkim), `service`(서비스 매핑), `sprint`(현재 월 YYYY-MM), `type_yt: feature`(기본)
- meeting: `date`(추출), `participants`(미정 시 jmkim만)
- daily: `date`(오늘)
- weekly-report: `year`, `month`, `week_in_month`, `assignee`
- okr: `year`, `quarter`, `scope: personal`(기본), `assignee`
- incident: `date`(오늘 또는 추출)
- capacity-plan: `year`, `month`, `assignees`(전체 dev role 4명)
- analysis/decision/proposal: `service_id`(추출)

미정 필드는 frontmatter에 빈 값으로 두지 않고 사용자에게 묻는다.

## llm-hint 블록

`_index.md`는 generate_vault_indexes.py가 처리. 일반 노트는 본문 위에 짧은 한 줄 hint 권장 (lint 강제 X, but 권장).

## 실행 지침

1. **입력 파싱** — 키워드·날짜·서비스명·DEV2-id·user 추출
2. **type 추정** — 결정 트리 적용. 모호 시 사용자 확인.
3. **위치·파일명 결정** — type 기반 dir + kebab-case slug
4. **frontmatter 채움** — 필수 필드 자동 추정 + 미정은 사용자 질문
5. **본문 템플릿** — type별 minimal 스켈레톤:
   - ticket: `## 배경`, `## 5W1H`, `## 진행 메모`
   - meeting: `## 참가자`, `## 아젠다`, `## 결정`, `## 후속`
   - daily: `## 오늘의 아젠다`, `## 진행`, `## 미해결`
   - decision: `## 배경`, `## 옵션`, `## 결정`, `## 근거`, `## 영향`
   - 기타: `## 개요`만
6. **dry-run 미리보기** — 사용자에게 `vault/wiki/processes/.../foo.md` 경로·frontmatter·본문 스켈레톤 보여줌
7. **사용자 confirm** → `Write` 도구로 생성
8. **lint check** — 즉시 `python3 harness/tools/lint_vault.py --vault {VAULT} --files {new}` 호출, exit 0 확인
9. **안내** — Obsidian에서 열고 본문 작성하라고 surface, `git add` + commit 시 pre-commit 한 번 더 검증됨

## 환경

| 변수 | 용도 |
|---|---|
| `VAULT` | vault 경로 (기본 `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`) |
| `HARNESS_ROOT` | harness repo (기본 `~/Documents/workspace/team2`) |
| `YOUTRACK_USER` | assignee 기본값 (기본 `jmkim`) |

## frontmatter 표준 (티켓 산출물)

```yaml
---
type: ticket
ticket_id: DEV2-XXXX
ticket_status: auto-prep | in-progress | done | backlog
assignee: jmkim
service: "[[max]]"      # 서비스 노트 wikilink (graph 엣지)
sprint: 2026-05
type_yt: feature | task | bug
---
```

상세: vault `wiki/guides/frontmatter-spec.md`.

## 템플릿 사용

본문 스켈레톤은 repo `$TEAM2_HARNESS_PATH/templates/vault-notes/{type}.md`가 SoT (Tolaria 호환 위해 vault 밖으로 분리 — vault 내 노트 스텁이 type 충돌·clutter 유발). 스킬은 type 결정 후 해당 템플릿 읽어 placeholder 치환.

치환 변수:
- `{{date}}` → 오늘 YYYY-MM-DD
- `{{title}}` → 사용자 입력에서 추출
- `{{user}}` → `$YOUTRACK_USER` 또는 `jmkim`
- `{{ticket_id}}`, `{{service_id}}`, `{{sprint}}`, `{{year}}`, `{{month}}`, `{{week_in_month}}`, `{{quarter}}`, `{{topic}}`, `{{topic_slug}}`, `{{domain}}`, `{{term}}` 등

미치환 placeholder는 그대로 두고 사용자가 Obsidian에서 채움.

## Obsidian 자동 오픈

vault에 파일 작성 + lint pass 후 자동으로 Obsidian에서 해당 파일 오픈:

```bash
$TEAM2_HARNESS_PATH/tools/obsidian_open.sh "{rel-path}"
```

내부적으로 `open "obsidian://open?vault=team2&file=..."` URI handler 호출. 사용자가 Obsidian app에서 즉시 본문 편집 가능.

## 사용자 확인 게이트

- 파일 생성 전 dry-run preview (dst·frontmatter·본문 헤더만)
- 모호한 type → 옵션 제시 + AskUserQuestion
- 기존 파일 충돌 → 덮어쓰기 vs 다른 이름 묻기
- 작성 후 Obsidian 자동 오픈 (사용자 선호 시 --no-open 옵션으로 끔)

## 환경 (추가)

| 변수 | 용도 |
|---|---|
| `OBSIDIAN_VAULT_NAME` | Obsidian 안 vault 이름 (기본 `team2`) |

ARGUMENTS: $ARGUMENTS
