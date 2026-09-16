---
name: youtrack-ticket-5w1h-ko
description: "Use when drafting or creating DEV2 YouTrack tickets in Korean, especially /ad:ticket, 5W1H ticket requests, issue creation, task splitting, assignee selection, story point sizing, or team2 ticket policy checks."
---

# DEV2 YouTrack 티켓 5W1H

이 스킬은 `/ad:ticket`의 Codex 진입점이다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/ticket.md`를 먼저 읽고 그 절차를 따른다. 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. command 파일이 참조하는 정책과 카탈로그만 추가로 읽는다.
4. 초안 작성까지는 자동 수행한다.
5. `POST /api/issues`, 담당자/필드 변경, 상태 변경, 삭제는 사용자 승인 후에만 실행한다.

## 고정 규칙

- 프로젝트는 기본 `DEV2`다.
- YouTrack은 REST API와 `curl`만 사용한다. MCP 도구는 사용하지 않는다 — 토큰과 쓰기 권한을 `curl` 한 경로로 통제하기 위해.
- `YOUTRACK_TOKEN`이 shell 환경에 없으면 `~/.claude/settings.json`의 `env.YOUTRACK_TOKEN`을 읽되 값을 출력하지 않는다.
- Feature는 1주 이하, Task는 1일 이하로 유지한다. 초과하면 분할을 제안한다.
- Feature 하위 Task는 개발 / 검증 / 배포·운영 반영 단계로 분리한다. 판정은 생략할 수 없고, 필요하면 별도 Task로 만들고 해당 없으면 Feature 본문에 사유를 남긴다. 하나의 Task에 개발과 검증, 배포를 섞지 않는다.
- 검증은 테스트(개발2팀 내부) / QA(시너지팀) / 테스트 후 QA 중 하나로 판정한다. 대부분은 내부 테스트다. `테스트 → QA`면 Task 2개로 나눈다.
- 등록 Task의 SP 상한은 3이다 — 넘으면 포인트를 올리지 않고 Task를 쪼갠다 (SoT `docs/sprint/story-point-guide.md` §4. 옛 "13점 금지·8점 분할"은 이 규칙에 흡수됨).
- 담당자 미설정 티켓을 만들지 않는다.

## 출력

사용자 승인 전에는 티켓 초안과 생성 예정 필드만 보여준다. 승인 표현이 모호하면 한 번 더 확인한다.
