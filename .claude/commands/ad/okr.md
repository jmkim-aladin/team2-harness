# OKR 조회 및 작성

팀/개인 OKR을 조회하거나, 분기 개인 OKR 초안을 작성합니다.

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

## 사용법

```
/ad:okr                          # 현재 분기 팀 OKR 조회
/ad:okr 연간                     # 연간 팀 OKR 조회
/ad:okr {N}분기                  # 해당 분기 팀(+개인) OKR 조회
/ad:okr 김정민                   # 해당 팀원의 OKR 전체 조회
/ad:okr 김정민 {N}분기 작성       # 분기 개인 OKR 초안 작성/수정
/ad:okr 동기화                   # YouTrack KB에서 최신 OKR 가져오기
```

## OKR 문서 위치 (Obsidian vault)

OKR 문서는 Obsidian vault `wiki/processes/okr/`에 저장된다. 절대 경로 베이스:
`/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/processes/okr/`

> **현재 상태 (2026-06 기준):** OKR 문서는 `team2-archive`에서 `wiki/processes/okr/`로 이관 완료(team/q1/q2 + 김정민 q1~q4 + q1 자기평가 + 조은흠 q2). 팀·김정민/조은흠 q2 등 KB 보유분은 KB 본문 기준으로 동기화함. **canonical은 YouTrack KB(REF-A-*)** — 이후 변경은 `/ad:okr 동기화`로 최신화한다. 연간 팀 OKR(`2026-team-okr.md`)은 분기 `quarter`가 없으므로 lint_vault okr 룰은 taxonomy(분기/연간 허용)에 맞춰 `required=[year,scope]` + 연간 파일명 허용으로 정렬됨.

| 파일 | 내용 | YouTrack KB |
|------|------|-------------|
| vault `wiki/processes/okr/2026-team-okr.md` | 팀 연간 OKR | REF-A-2175 |
| vault `wiki/processes/okr/2026-q1-team-okr.md` | 1분기 팀 + 개인별 OKR | REF-A-2470 |
| vault `wiki/processes/okr/2026-q2-team-okr.md` | 2분기 팀 OKR (담당자·월 배정) | REF-A-3122 |
| vault `wiki/processes/okr/2026-q3-team-okr.md` | 3분기 팀 OKR | REF-A-4032 |
| vault `wiki/processes/okr/2026-q1-kimjeongmin.md` | 김정민 1분기 개인 OKR | REF-A-2566 |
| vault `wiki/processes/okr/2026-q2-kimjeongmin.md` | 김정민 2분기 개인 OKR | - |
| vault `wiki/processes/okr/2026-q2-joeunheum.md` | 조은흠 2분기 개인 OKR | - |
| vault `wiki/processes/okr/2026-q3-kimjeongmin.md` | 김정민 3분기 작업용 초안 (조정 이력·Baseline lock·메모) | DEV2-A-1265 |
| vault `wiki/processes/okr/2026-q3-kimjeongmin-final.md` | 김정민 3분기 최종본 (KB 반영용 클린) | DEV2-A-1265 |
| vault `wiki/processes/okr/2026-q3-kimjeongmin-candidates.md` | 김정민 3분기 KR 후보 풀 | - |
| vault `wiki/processes/okr/2026-q4-kimjeongmin.md` | 김정민 4분기 개인 OKR | - |

### 파일명 규칙

- 작업용 초안: `{year}-q{N}-{이름접미사}.md` — 조정 이력·Baseline lock 현황·제외/위임·보완 필요 메모 포함
- 최종본: `{year}-q{N}-{이름접미사}-final.md` — KB 반영용. 메타 표기(분모 lock 날짜, 후보 코드, 조정 이력) 없이 내용만
- KR 후보 풀(선택): `{year}-q{N}-{이름접미사}-candidates.md`

## 팀원 이니셜 매핑

| 이니셜 | 이름 | 구분 | 파일명 접미사 |
|--------|------|------|--------------|
| KJM | 김정민 | 정규 | kimjeongmin |
| JEH | 조은흠 | 정규 | joeunheum |
| JJY | 조윤주 | 정규 | joyunju |
| AHR | 안혜련 | 정규 | anhyeryeon |
| LHM | 이현민 | 정규 | leehyunmin |
| KJS | 김정실 | 정규 | kimjeongsil |
| LYR | 이유림 | 정규 | leeyurim |
| IYK | 강인용 | 정규 | kanginyong |
| PMS | 박민석 | 정규 | parkminseok |
| JYJ | 조주영 | 프리랜서 | jojuyoung |
| PHS | 박희수 | 프리랜서 | parkheesu |

## 실행 지침

### 조회 모드

1. 사용자 요청에 맞는 vault `wiki/processes/okr/` 파일을 읽어서 표시 (파일이 없으면 — 현재 기본 상태 — `/ad:okr 동기화`를 먼저 실행하거나 KB `REF-A-*`를 직접 조회)
2. 팀원 이름으로 요청 시 해당 팀원의 모든 분기 OKR을 조회
3. 팀 OKR 조회 시 담당자 배정 현황도 함께 표시

### 작성 모드

개인 OKR 초안 작성 시 아래 원칙을 따릅니다:

1. **팀 OKR에서 담당 항목 추출**: vault `wiki/processes/okr/{year}-q{N}-team-okr.md`에서 해당 팀원이 배정된 KR 항목을 식별
2. **전분기 OKR·마감 노트 참조**: 해당 팀원의 전분기 개인 OKR + 스프린트 마감 노트(`wiki/processes/sprint/`)로 실적·이월 파악 — 전분기 실적 코멘트의 근거
3. **연간 OKR 정렬**: 연간 목표와의 연결고리 확인
4. **팀장 리뷰 회의록 반영**: vault `wiki/processes/meetings/`에서 OKR 조정 지침(범위 축소·지표 기준 등)이 있으면 우선 반영

#### OKR 작성 규칙 (2026-07 팀장 리뷰 기준)

- **Objective**: 해당 분기에 담당자가 달성할 핵심 목표를 1문장으로 (팀 KR과 연계)
- **KR 구조**: `### KR{n}` 아래 `#### KR{n}-{m}` sub-KR로 분리 — 항목별로 선택/제거 가능한 단위. 각 sub-KR에 팀 KR 연계 명시
- **지표 = 모수 고정 필수**: 모든 지표는 분모(baseline)를 명시한 `n건 중 n건` 형식. 분모는 티켓 수·티켓 목록 기반으로 확정 (막연한 "완료율 100%" 금지 — 모수가 흔들리면 안 됨)
  - 분모 lock 후 축소 금지. 신규 편입은 추가만 허용
  - 분모 미확정 지표는 확정 방법·시점을 명시하고 작업용 초안의 "Baseline lock 현황" 표에서 관리
  - 담당이 본인이 아닌 티켓은 분모에 넣지 않는다 (관련만 있는 타 담당 티켓 제외)
- **케이스 지표는 전량 인라인**: 테스트 케이스·검증 항목은 별도 부록 없이 KR 본문에 전 목록 나열. 케이스 묶음 라인에 담당 검증 Task ID 병기
- **전분기 실적 코멘트 섹션 필수**: KR별 결과·저조/이월 사유 표 + 구조 요인. 범위 축소·지표 조정의 배경 설명
- **월별 포커스 테이블 사용 안 함**: 월별 배분은 스프린트 운영(Sprints 필드)에서 관리
- **협업 포인트**: 다른 팀원과 동시 진행되는 항목이 있으면 동기화 포인트 표시

#### 티켓 연결 규칙 (KB 자동 링크)

- 각 지표/번호 항목 하위에 해당 티켓을 **라벨 없이** `DEV2-XXXX {실제 티켓 제목}` 형식으로 나열 — KB에서 자동 링크됨
- Feature → Task 들여쓰기 트리로 건건 연결. 번호 지표(1. 2. 3.)와 티켓은 1:1로 해당 번호 하위에 중첩
- 기존 티켓을 참조할 때도 실제 제목을 API로 조회해 병기

#### OKR → 티켓 발행 플로우

1. KR 확정 후 sub-KR별 Feature/Task 후보 정리 (기존 재사용 vs 갭 신규 구분)
2. `/ad:ticket`으로 일괄 발행 — 기본: Backlog, 스프린트 미배정, Feature SP 0 / Task SP 1~3, Subtask 링크, `role:`/`biz:` 태그
3. 발행된 Feature 목록으로 분모 lock (예: "착수 Feature n건 중 n건")
4. OKR 문서(작업용 + 최종본)에 티켓 건건 연결, frontmatter `related_tickets` 갱신

#### 출력 형식 (최종본 기준)

```markdown
# {이름} {year} {N}분기 개인 OKR

> 상위: REF-A-XXXX ({N}분기 팀 OKR) | REF-A-2175 (연간 팀 OKR)
> 작업용 초안: [[{year}-q{N}-{이름접미사}]]

## Objective
{1문장 핵심 목표}

## {N-1}분기 실적 코멘트
| Q{N-1} KR | 결과 | 사유 |
...

## Key Results

### KR1. {제목}
> 팀 KR{N} 연계 — {팀 KR 내용 요약}

#### KR1-1. {sub-KR 제목}
- {지표} **n건 중 n건** {완료 기준}
  1. {항목}
     - DEV2-XXXX {티켓 제목}
       - DEV2-XXXX {하위 Task 제목}
  2. {항목}
     - DEV2-XXXX {티켓 제목}
...

## 제외·위임
| 구 KR | 처리 |
...
```

### YouTrack 동기화 모드

1. YouTrack KB API로 최신 OKR 문서 조회
2. vault `wiki/processes/okr/`의 기존 문서와 비교
3. 변경 사항이 있으면 업데이트

```bash
BASE="https://aladincommunication.youtrack.cloud"
# 팀 연간 OKR
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-2175?fields=id,idReadable,summary,content,updated"
# 1분기
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-2470?fields=id,idReadable,summary,content,updated"
# 2분기
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-3122?fields=id,idReadable,summary,content,updated"
# 3분기
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-4032?fields=id,idReadable,summary,content,updated"
# 김정민 3분기 개인 (DEV2 KB)
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/DEV2-A-1265?fields=id,idReadable,summary,content,updated"
```

> vault 파일에 linter가 괄호를 `\(`로 이스케이프할 수 있음 — 문자열 매칭 편집 시 이스케이프 변형 허용 필요. Edit 도구가 iCloud 경로에서 간헐 EPERM을 내면 python 파일 쓰기로 우회.

## 스프린트 연계

OKR 작성 시 스프린트 운영 문서도 참조합니다:
- `docs/sprint/sprint-planning-overview.md` — 맨데이 배분 및 계획 업무 비율
- `docs/sprint/story-point-guide.md` — SP 산정 기준
- `docs/sprint/ticket-guide.md` — 티켓 작성 규칙

## OKR 문서 frontmatter

```yaml
---
type: okr
title: 김정민 2026 3분기 개인 OKR
canonical_id: okr:2026-Q3-jmkim        # 최종본은 -final 접미사
status: draft | canonical
year: 2026
quarter: 3
scope: team | personal
assignee: jmkim  # personal일 때
updated_at: 2026-07-09
---
```

> `related_tickets`는 vault 자동 백필(auto-backfill)이 본문 DEV2 ID 기준으로 채움 — 수동 관리 불필요.

ARGUMENTS: $ARGUMENTS
