# team2 공통 메모리 (Claude Code)

> SoT: team2 repo `memory/claude-base.md`. `~/.claude/team2-base.md` 는 이 파일의 심볼릭 링크다 — 직접 편집하지 말고 repo 에서 PR 로 바꾼다.

## 세션 컨텍스트 규율

모델이 날카롭게 추론하는 대역은 **smart zone**(약 150k 토큰). 다음을 지켜 창을 zone 안에 둔다.

- **단계 경계에서 비운다.** 각 구현 앞에서 `/clear`. 판단은 경계에서만 하고, 순서는 계속 → `/clear` → handoff → 서브에이전트 → `/compact`
- **파일은 Read로 읽는다.** `cat`/`head`/`tail`/`sed`로 파일 내용을 출력하지 않는다. Bash는 실행이 목적일 때만
- **절대 경로로 명령한다.** 셸 cwd는 호출마다 초기화되므로 `cd`로 재진입하지 않는다
- **한 번 읽은 파일은 다시 읽지 않는다.** 다시 필요하면 스크래치에 요약을 남기고 그것을 참조
- **넓은 조사는 서브에이전트로 보내고 결론만 회수한다** (`Explore`, `caveman:cavecrew-investigator`)

근거: 2026-08-08 30일 실측 — 호출당 평균 컨텍스트 470k(zone의 3배), Bash가 호출의 64.9%, 그중 `cd` 4,152회.

## 작업 플로우

```
정렬 → 스펙+분할 → 착수 준비 → 구현 → 리뷰 → 종료
```

| 단계 | 명령 | 하는 일 |
|---|---|---|
| 정렬 | `/grill-with-docs` | 설계 트리를 소진할 때까지 frontier 라운드 인터뷰 + 용어집·결정 인라인 기록 |
| 스펙+분할 | `/ad:ticket` | 5W1H Feature 발행 → Task 분할 |
| 착수 준비 | `/ad:work-prep` | 위키 노트 + 코드 진입점 + 컨텍스트 묶기 |
| 구현 | `/implement` (내부 `tdd` 구동) | 사전 합의된 seam에서 red→green, 마감 리뷰는 `/ad:code-review` |
| 리뷰 | `/ad:code-review` | 기준축·스펙축 분리 판정 |
| 종료 | `/ad:work-close` | 소요시간 기록 + 티켓 종료 |

온램프: 버그 → `diagnosing-bugs`(모델 호출) 또는 `/investigate` / 프로토타입 필요 → `prototype` / 대형 안개 과제 → `/wayfinder` / 데이터 추출 → `/ad:data-request` / 월말 → `/ad:sprint-close-check`, `/ad:capacity-plan`

규모별: 1시간 이내(오타·설정) 바로 처리 / 반나절(버그) 준비→구현→리뷰 / 1일 이상 전체 플로우.

### 단계 경계

- 정렬 → 분할은 한 창에서 끊지 않는다
- 각 구현 앞에서 `/clear` — 티켓은 자족적이므로 앞 티켓 컨텍스트는 버린다

### 팀 규칙 우선

- 단계 분리(개발/검증/배포)는 조직 현실 기반 수평 분할 — 수직 슬라이스는 개발 Task 내부에만
- spec은 YouTrack Feature 본문(5W1H). 별도 spec 파일을 만들지 않는다
- gstack 스킬은 `policies/gstack-override-policy.md`, mattpocock 스킬은 `policies/overrides/mattpocock.md`가 우선
- mattpocock 스킬의 이슈 트래커·도메인 문서 설정: `$TEAM2_HARNESS_PATH/docs/agents/` (issue-tracker.md, domain.md). repo 루트 CONTEXT.md 를 만들지 않는다
