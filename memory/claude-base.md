# team2 공통 메모리 (Claude Code)

> SoT: team2 repo `memory/claude-base.md`. `~/.claude/team2-base.md` 는 이 파일의 심볼릭 링크다 — 직접 편집하지 말고 repo 에서 PR 로 바꾼다.

## 세션 컨텍스트 규율

모델이 날카롭게 추론하는 대역은 **smart zone**(약 150k 토큰). 다음을 지켜 창을 zone 안에 둔다.

- **단계 경계에서 비운다.** 각 구현 앞에서 `/clear`. 판단은 경계에서만 하고, 순서는 계속 → `/clear` → handoff → 서브에이전트 → `/compact`
- **파일은 Read로 읽는다.** `cat`/`head`/`tail`/`sed`로 파일 내용을 출력하지 않는다. Bash는 실행이 목적일 때만
- **절대 경로로 명령한다.** 셸 cwd는 호출마다 초기화되므로 `cd`로 재진입하지 않는다
- **한 번 읽은 파일은 다시 읽지 않는다.** 다시 필요하면 스크래치에 요약을 남기고 그것을 참조
- **가이드·정책 문서는 절 단위로 소비한다.** 통째 Read 대신 목차(`grep -n '^## '`) → 해당 절만 Read offset. 스킬이 절 번호를 지목하면 그 절만 (근거: ticket-guide 35KB 전체 재독 14회/월 실측)
- **넓은 조사는 서브에이전트로 보내고 결론만 회수한다** (`Explore`, `caveman:cavecrew-investigator`)

근거: 2026-08-08 30일 실측 — 호출당 평균 컨텍스트 470k(zone의 3배), Bash가 호출의 64.9%, 그중 `cd` 4,152회.

## 작업 플로우

```
정렬 → 스펙+분할 → 착수 준비 → 구현 → 리뷰 → 종료
```

| 단계 | 명령 | 하는 일 |
|---|---|---|
| 정렬 | `/ad:grill` | `grilling`+`domain-modeling` — frontier 라운드, 용어집·결정 기록 |
| 스펙+분할 | `/ad:ticket` | 5W1H Feature 발행 → Task 분할 |
| 착수 준비 | `/ad:work-prep` | 위키 노트 + 코드 진입점 + 컨텍스트 묶기 |
| 구현 | `/ad:implement` | vendored `implement`(내부 `tdd`) — seam 합의, red→green |
| 리뷰 | `/ad:code-review` | 기준축·스펙축 분리 판정 |
| 종료 | `/ad:work-close` | 소요시간 기록 + 티켓 종료 |

온램프: 버그 → `diagnosing-bugs`(모델 호출) 또는 `/investigate` / 프로토타입 필요 → `prototype` / 대형 안개 과제 → `/wayfinder` / 데이터 추출 → `/ad:data-request` / 월말 → `/ad:sprint-close-check`, `/ad:capacity-plan`

규모별: 1시간 이내(오타·설정) 바로 처리 / 반나절(버그) 준비→구현→리뷰 / 1일 이상 전체 플로우.

### 단계 경계

- 정렬 → 분할은 한 창에서 끊지 않는다
- 각 구현 앞에서 `/clear` — 티켓은 자족적이므로 앞 티켓 컨텍스트는 버린다
- **다음 단계가 조향 없이 돌 수 있으면**(스코프 확정 + headless 검증 루프) 새 세션이 아니라 **서브에이전트**로 보낸다. 사람 확인 지점(시각 확인·커밋 게이트)만 남긴다. 오래 걸리고 중간 조향이 필요하면 `/ad:orchestration`(Herdr pane), 판단·취향이 계속 끼면 사람 세션

### 서브에이전트 위임 — 업무별 모델 판단

위임 왕복 오버헤드(스폰 + 컨텍스트 로드 + 결과 회수)보다 이득이 클 때만. 애매하면 직접.

| 업무 | 모델 | 방식 |
|---|---|---|
| 단순 편집 (오타·리네임·1~2파일) | 위임 안 함 | 직접 — 오버헤드가 작업보다 큼 |
| 기계적 탐색 (위치·레퍼런스·디렉토리 맵) | haiku | Explore (caveman 있으면 `cavecrew-investigator`) |
| 의미 파악 조사 (플로우 추적·구조 요약) | sonnet | Explore |
| 일반 코딩 (패턴 미러링·버그 수정·테스트 작성) | opus | general-purpose. 검증 루프(lint·build·test)와 완료 기준을 프롬프트에 명시, **커밋 금지** — 게이트는 메인 |
| 리뷰 1차 스캔 | sonnet | `cavecrew-reviewer` — 최종 판정은 메인 |
| 설계·아키텍처·까다로운 디버깅·게이트 판정 | 위임 부적합 | 메인 유지 |

- 모델 미지정 시 세션 모델 상속 — 지정은 위 표처럼 확신 있을 때만
- 서브에이전트 결과물은 메인에서 diff 확인 후 사용자에게 보고한다

#### 위임 프롬프트 계약 — 5요소

<!-- canonical:delegation-contract targets=AGENTS.md -->
절차를 쪼개 순서대로 시키지 말고 **일을 통째로** 준다. 다섯 요소를 모두 채우면 자족적이다.

| 요소 | 내용 |
|---|---|
| **목표** | 끝난 상태를 한 문장. 경로·순서는 지정하지 않는다 |
| **의도(왜)** | 누구를 위해, 무엇이 가능해지는가. 미리 못 정한 결정을 서브에이전트가 이 맥락으로 판단한다 |
| **불변조건** | 각 항에 이유를 붙인 긍정형. 앵커 문서 경로(티켓 노트·정책·카탈로그)와 repo 관례를 여기 건다 |
| **완료 기준** | 기계 판정 가능한 신호 — 통과할 명령(lint·build·test), 존재할 파일, 만족할 수치 |
| **출력 형식** | 회수할 산출물의 모양과 길이. 안 적으면 장황해진다 |

- 커밋·푸시·티켓 상태 변경은 서브에이전트가 하지 않는다 — 게이트는 메인 (근거: 사용자 확인 게이트는 invariant)
- 부정형 나열("~하지 마라")로 가드레일을 채우지 않는다. 대체 행동이 비면 모델이 그 자리를 임의로 채운다 — `policies/instruction-precedence-policy.md` §표기 규약
- "다시 검증하라", "단계별로 생각하라" 같은 사고 과정 지시는 넣지 않는다. 신모델 내장 행동이라 중복 단계와 토큰만 늘린다. 산출물에 남길 증거(출처·파일:행·통과 명령)를 요구하는 것은 이와 다르며 유지한다

근거: 2026-09-16 Anthropic Claude 5 세대 가이드 — 완전한 작업 명세(목표·가드레일·종료 조건)를 주고 끝까지 돌리는 쪽이 단계 지시보다 낫다.
<!-- /canonical:delegation-contract -->

### 팀 규칙 우선

- 단계 분리(개발/검증/배포)는 조직 현실 기반 수평 분할 — 수직 슬라이스는 개발 Task 내부에만
- spec은 YouTrack Feature 본문(5W1H). 별도 spec 파일을 만들지 않는다
- gstack 스킬은 `policies/gstack-override-policy.md`, mattpocock 스킬은 `policies/overrides/mattpocock.md`가 우선
- mattpocock 스킬의 이슈 트래커·도메인 문서 설정: `$TEAM2_HARNESS_PATH/docs/agents/` (issue-tracker.md, domain.md). repo 루트 CONTEXT.md 를 만들지 않는다
