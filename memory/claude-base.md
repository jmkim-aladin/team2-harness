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

## Skill invocation

스킬은 요청이 맞으면 호출하되, `superpowers:using-superpowers`의 자동 호출 지시(1% 규칙, 응답 전 스킬 스캔, 체크리스트 todo 강제)는 적용하지 않는다.

근거: 2026-08-08 실측 — superpowers 28종 중 실사용 3종. 매 턴 스캔 강제가 지연 유발.

## 작업 플로우

```
정렬 → 스펙+분할 → 착수 준비 → 구현 → 리뷰 → 종료
```

| 단계 | 명령 | 하는 일 |
|---|---|---|
| 정렬 | (신설 예정 `/ad:grill`) — 그때까지 `superpowers:brainstorming` | 설계 트리를 소진할 때까지 인터뷰 |
| 스펙+분할 | `/ad:ticket` | 5W1H Feature 발행 → Task 분할 |
| 착수 준비 | `/ad:work-prep` | 위키 노트 + 코드 진입점 + 컨텍스트 묶기 |
| 구현 | (신설 예정 `/ad:implement`) — 그때까지 직접 + TDD | 사전 합의된 seam에서 red→green |
| 리뷰 | `/ad:code-review` | 기준축·스펙축 분리 판정 |
| 종료 | `/ad:work-close` | 소요시간 기록 + 티켓 종료 |

온램프: 버그 → `/investigate` / 데이터 추출 → `/ad:data-request` / 월말 → `/ad:sprint-close-check`, `/ad:capacity-plan`

규모별: 1시간 이내(오타·설정) 바로 처리 / 반나절(버그) 준비→구현→리뷰 / 1일 이상 전체 플로우.

### 단계 경계

- 정렬 → 분할은 한 창에서 끊지 않는다
- 각 구현 앞에서 `/clear` — 티켓은 자족적이므로 앞 티켓 컨텍스트는 버린다

### 팀 규칙 우선

- 단계 분리(개발/검증/배포)는 조직 현실 기반 수평 분할 — 수직 슬라이스는 개발 Task 내부에만
- spec은 YouTrack Feature 본문(5W1H). 별도 spec 파일을 만들지 않는다
- gstack 스킬은 `policies/gstack-override-policy.md`가 우선
