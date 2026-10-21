# 외부 스킬 팩 3종 통합 판정 — Pocock · pstack · Osmani

검토일: 2026-10-21. 계기: Rob Shocks 영상 [Pocock vs Pstack vs Osmani](https://www.youtube.com/watch?v=sU9MW8Ycq2M). 앞선 개별 판정: mattpocock은 [오버라이드 정책](../policies/overrides/mattpocock.md), pstack은 [적용 검토](pstack-harness-adoption-review.md)(2026-09-14). 이 문서는 세 팩을 한 기준에 놓고 이번에 가져온 것과 가져오지 않은 것을 기록한다. 보조 장치의 이름과 위치는 [harness-guide.md](harness-guide.md) §단계별 도구 명칭이 SoT다.

## 판단

**세 팩 모두 통째로 설치하지 않는다. 필요한 것만 기존 단계에 강도별로 흡수한다.** 새 동사(`/ad:*`)와 새 상주 description은 0개다. 가져온 것은 기존 동사·엔진 아래 보조 장치로 붙였고, 무거운 장치는 강도가 위험일 때만 켜진다.

| 팩 | 관점 | 팀에서의 자리 |
|---|---|---|
| Pocock ([mattpocock/skills](https://github.com/mattpocock/skills)) | **합의** — 무엇을 만들지 먼저 맞춘다. 문제가 흐릿할 때, 오래 살 코드의 설계를 다룰 때 | 정렬·구현 엔진. 17종 vendor |
| pstack ([cursor/plugins](https://github.com/cursor/plugins/tree/5bf2b1544db739998121a306340631963c2ff3de/pstack)) | **실행 증명** — 빌드 통과는 증거가 아니다. 재현 안 되는 버그, 마이그레이션, 장시간 실행 | 리뷰 증거·디버깅. 컨셉만 흡수 |
| Osmani ([addyosmani/agent-skills](https://github.com/addyosmani/agent-skills/tree/aeac41d)) | **전 과정·팀 친화** — 스펙부터 CI/CD·관측성·폐기·출시까지 품질 게이트를 갖춘 예측 가능한 절차 | 설계 검증·리뷰·DoD의 빈칸. 이번 검토 |

영상의 결론 세 가지가 판정 기준이다.

1. **절차의 무게는 위험에 맞춘다** — 버튼 색을 바꾸는 데 PRD·작업 분할·보안 감사는 필요 없다. 운영·보안·비가역이면 전체 리뷰와 반증 검토를 꺼낸다 [10:01–10:37]
2. **가지치기** — 모든 프로젝트에 모든 스킬은 과하다. 스킬마다 에이전트가 고려할 대상이 늘고 원치 않는 자동 발동이 생긴다. 모델이 강해진 만큼 기존 스킬을 줄인다 [09:13–09:45], [10:46–11:03]
3. **훔쳐서 자기 하네스를 만든다** — 팩은 교과서다. 통하는 것을 가져와 자기 품질 기준 위에 쌓는다. 에이전트가 실수하면 스킬을 고친다 [11:49–12:21]

팀은 이미 2번을 겪었다 — superpowers(2026-08-08)와 gstack(2026-09-28)을 설치했다가 트리거 중복·상주 비용으로 걷어냈다([CLAUDE.md](../CLAUDE.md) §외부 스킬). 그래서 1번은 [강도](harness-guide.md)(가벼움·보통·무거움·위험)로, 3번은 아래 표의 개별 흡수로 푼다. 판정 근거는 [하네스 북극성](../policies/harness-north-star.md)·[스킬 작성 원칙](../policies/skill-authoring-principles.md) §1 트리거·§4 가지치기다.

## 검토 범위와 근거

- Osmani: 커밋 `aeac41d`(plugin 0.6.13). 스킬 25개, 에이전트 4개, 명령 9개, 훅 3종(session-start·simplify-ignore·sdd-cache), references, evals를 읽었다. 원문은 신뢰하지 않는 데이터로 읽었고 설치·실행하지 않았다
- pstack: 앞선 검토의 고정 커밋 `5bf2b15` 재사용. 이번에 새로 본 것은 `why`·`reflect`·`architect` 컨셉
- Pocock: vendor 사본 [vendor/mattpocock/](../vendor/mattpocock/)(`6acc160e`, v1.2.3)
- 영상: 자막 타임스탬프로 인용
- 로컬 비교: team2 `team2/agent-skills-absorb` 작업 트리(미커밋 변경 포함). 서비스 repo 적용·실제 PR 리뷰 실행은 하지 않았다

## 팀의 각 팩 현황

| 팩 | 현황 | 근거 |
|---|---|---|
| Pocock | 17종 vendor, 8종 제외. 동사층 wrapper `/ad:grill`·`/ad:implement`가 진입점 | [오버라이드 정책](../policies/overrides/mattpocock.md) |
| pstack | 설치 없음. B01–B10 블록으로 실행 검증 계약·행동 평가·리뷰 증거 컨셉 흡수 | [적용 검토](pstack-harness-adoption-review.md), [반영 내역](pstack-harness-implementation.md) |
| Osmani | 설치 없음. 이번에 개별 항목 흡수 | 이 문서 |

## 이번에 가져온 것 — 2026-10-21

북극성 열은 [하네스 북극성](../policies/harness-north-star.md) 원칙 번호다(1 검증 루프 · 2 문제 통째 · 3 컨텍스트 · 4 환경=진실 · 5 게이트 기계화 · 6 아티팩트 기억).

| 정식 명칭 | 출처 (팩·스킬) | 적용 위치 | 북극성 |
|---|---|---|---|
| 강도 | 영상 [10:01] "ceremony should match the stakes" · Osmani [adoption-guide](https://github.com/addyosmani/agent-skills/blob/aeac41d/docs/adoption-guide.md)(점진 도입) | [harness-guide.md](harness-guide.md) §강도, 티켓 노트 `## 구현 계획`의 `강도:` 줄 | 3·5 |
| 단계별 도구 명칭 (단계×강도 지도) | 영상 [07:53] light·medium·heavy 런타임 | [harness-guide.md](harness-guide.md) §단계별 도구 명칭 | 3 |
| 구현 계획 · 완료 조건 · 슬라이스 · 구현 중 신호 | Osmani [planning-and-task-breakdown](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/planning-and-task-breakdown/SKILL.md)·[spec-driven-development](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/spec-driven-development/SKILL.md)·[incremental-implementation](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/incremental-implementation/SKILL.md), 검증 명령은 pstack [create-verification-skill](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/create-verification-skill/SKILL.md) | [work-prep-note-template.md](sprint/work-prep-note-template.md) §구현 계획, [`/ad:implement`](../.claude/commands/ad/implement.md) | 2·6 |
| 근거 등급 | pstack [why](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/why/SKILL.md)(사실·추론·미확인 구분) | [work-prep-note-template.md](sprint/work-prep-note-template.md) | 6 |
| 멱등키 계약 | Osmani [api-and-interface-design](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/api-and-interface-design/SKILL.md) §6 | [review-sections.md](eng-review/review-sections.md) §1 아키텍처 | 4 |
| Expand/Contract | Osmani [deprecation-and-migration](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/deprecation-and-migration/SKILL.md) | [review-sections.md](eng-review/review-sections.md) §1 아키텍처 | 4 |
| 성능 판정 규칙 · 시도 기록 | Osmani [performance-optimization](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/performance-optimization/SKILL.md) | [review-sections.md](eng-review/review-sections.md) §4 성능 | 1·6 |
| 사용 예 선행 설계 | pstack [architect](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/architect/SKILL.md) | `/ad:eng-review` — [harness-guide.md](harness-guide.md) §단계별 도구 명칭 | 2 |
| 반증 검토 (doubt review) | Osmani [doubt-driven-development](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/doubt-driven-development/SKILL.md) — 원본은 비자명한 결정 전부, 팀은 위험 강도의 비가역 결정만 | `/ad:eng-review` — [harness-guide.md](harness-guide.md) §단계별 도구 명칭 | 1 |
| 완화 신호 스캔 (floor guard) | Osmani [constraint-driven-development floor-guard](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/constraint-driven-development/references/floor-guard.md) | [tools/gate_loosening_scan.py](../tools/gate_loosening_scan.py), [`/ad:code-review`](../.claude/commands/ad/code-review.md) 1단계 | 1·5 |
| 페르소나 리뷰 (보안 감사 / 테스트 엔지니어 / 데이터 정합성 감사) | Osmani [security-auditor](https://github.com/addyosmani/agent-skills/blob/aeac41d/agents/security-auditor.md)·[test-engineer](https://github.com/addyosmani/agent-skills/blob/aeac41d/agents/test-engineer.md) 번안 + [orchestration-patterns](https://github.com/addyosmani/agent-skills/blob/aeac41d/references/orchestration-patterns.md)(병렬 fan-out, 페르소나 간 호출 금지). 데이터 정합성 감사는 팀 신설 | [code-review/personas.md](code-review/personas.md) | 2·3 |
| 안전 가정 입증 (blast radius) | pstack [blast-radius](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/blast-radius/SKILL.md) | [code-review/personas.md](code-review/personas.md) §안전 가정 입증, `/ad:code-review` §검증 순서 | 1·4 |
| SP 중복 호출 판정 | Osmani api-and-interface-design §6을 MSSQL SP로 번안 | [code-review-policy.md](../policies/code-review-policy.md) §SP 중복 호출 판정 | 4 |
| 경쟁 가설 조사 | pstack [arena](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/arena/SKILL.md)·[swarm](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/swarm/SKILL.md) | `diagnosing-bugs` + `/ad:orchestration` — [harness-guide.md](harness-guide.md) §단계별 도구 명칭 | 1 |
| DoD 체크리스트 — 변경 전 실패 증거 | Osmani [definition-of-done](https://github.com/addyosmani/agent-skills/blob/aeac41d/references/definition-of-done.md) | [dod-checklist.md](../templates/dod-checklist.md) | 1 |
| 롤백 트리거 | Osmani [shipping-and-launch](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/shipping-and-launch/SKILL.md) | `/ad:work-close` — [harness-guide.md](harness-guide.md) §단계별 도구 명칭 | 5 |
| 승인 응답 판별 | Osmani [interview-me](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/interview-me/SKILL.md) | [instruction-precedence-policy.md](../policies/instruction-precedence-policy.md) §승인 응답 판별 | 5 |

번안 원칙 세 가지:

- **위치는 기존 단계 아래** — 새 진입점을 만들지 않았다. 페르소나도 `.claude/agents`가 아니라 `/ad:code-review`가 위험 강도에서만 읽는 프롬프트 파일이다. Claude Code와 Codex가 같은 파일을 쓰고, 평소 세션의 상주 비용은 0이다
- **기준은 한 곳** — 페르소나·명칭 표는 정책·eng-review 절을 링크로만 참조한다. 같은 기준을 두 곳에 쓰면 한쪽이 낡는다
- **팀 경계 유지** — DB 스크립트·SP PR은 비즈니스 로직만 본다(배포 산출물 제외), 게시·커밋은 사용자 확인 게이트를 그대로 지난다

### Pocock — 새로 가져온 것은 없다. 묻혀 있던 엔진을 지도에 올렸다

아래는 이미 vendor된 엔진이다. 지도 하단 상황표에 흩어져 있어 "지금 쓸 때"라는 신호가 약했다. 설치가 아니라 단계별 지도에 신호와 함께 올렸다([harness-guide.md](harness-guide.md) §작업 플로우).

| 엔진 | 쓰는 신호 | 지도 자리 |
|---|---|---|
| [`/wayfinder`](../vendor/mattpocock/wayfinder/) | **과제 크기 판정** — 미결 결정이 여럿이고 세션을 넘는 안개 과제. wayfinder 맵(YouTrack 결정 티켓 지도)을 프런티어에서 하나씩 풀고 길이 보이면 `/ad:ticket`으로 합류. 트래커 매핑은 [issue-tracker.md](agents/issue-tracker.md) §Wayfinding operations로 이미 연결돼 있다 | §1 구상 과제 크기 판정 분기 |
| [`prototype`](../vendor/mattpocock/prototype/) | 설계 질문을 코드로 답해야 할 때(상태 모델·UI) | §1 구상 |
| [`research`](../vendor/mattpocock/research/) | 문서·API 1차 자료 조사를 백그라운드로 위임 | §1 구상 |
| [`/to-questionnaire`](../vendor/mattpocock/to-questionnaire/) | 다른 조직에 결정 질문을 보낼 때 | §1 구상 |
| [`/handoff`](../vendor/mattpocock/handoff/) | 세션·사람·하네스 사이 인계 | 상시 |
| [`/wait-what`](../vendor/mattpocock/wait-what/) · [`/teach`](../vendor/mattpocock/teach/) | 방금 설명이 안 읽힐 때 재설명 / 새 기술의 다세션 학습 | 상시 |

## 가져오지 않은 것

| 항목 | 원본의 특성 | 팀 판단 |
|---|---|---|
| Osmani 플러그인 통째 설치 | 스킬 25개 description 상주, 단계별 명령 9개 | 상주 비용과 트리거 중복. superpowers·gstack 제거 이력과 같은 패턴이다. 원작자도 점진 도입을 권한다([adoption-guide](https://github.com/addyosmani/agent-skills/blob/aeac41d/docs/adoption-guide.md), 영상 [10:38]) |
| `SPEC.md` · `tasks/plan.md` · `tasks/todo.md` | spec·계획·할 일을 repo 파일로 관리 | 팀 규칙은 spec = YouTrack Feature 본문(5W1H)이다. 계획은 vault 티켓 노트 `## 구현 계획`이 맡는다 |
| [using-agent-skills](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/using-agent-skills/SKILL.md) · [SessionStart 훅](https://github.com/addyosmani/agent-skills/blob/aeac41d/hooks/session-start.sh) | 세션 시작 시 라우터 메타 스킬 주입 | Claude Code는 description이 라우팅이라 이중 라우팅이 된다. 팀은 라우팅 블록을 걷어낸 이력이 있다([스킬 작성 원칙](../policies/skill-authoring-principles.md) §1, mattpocock `ask-matt` 제외) |
| [web-performance-auditor](https://github.com/addyosmani/agent-skills/blob/aeac41d/agents/web-performance-auditor.md) · [frontend-ui-engineering](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/frontend-ui-engineering/SKILL.md) · [browser-testing-with-devtools](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/browser-testing-with-devtools/SKILL.md) | 웹 성능·프론트엔드·브라우저 | 팀 주력은 백엔드(Kotlin·.NET·SP)다. 프론트 수요가 생기면 재검토 |
| [simplify-ignore](https://github.com/addyosmani/agent-skills/blob/aeac41d/hooks/SIMPLIFY-IGNORE.md) · [sdd-cache](https://github.com/addyosmani/agent-skills/blob/aeac41d/hooks/SDD-CACHE.md) 훅 | 단순화 보호 마커, spec 캐시 훅 | 팀 사용 패턴 대비 과하다. 훅 유지·디버깅 비용이 이득보다 크다 |
| [context-engineering](https://github.com/addyosmani/agent-skills/blob/aeac41d/skills/context-engineering/SKILL.md) | 컨텍스트 설정 가이드 | 팀이 더 강하다 — smart zone 규율과 `tools/harness_context_audit.py` 측정까지 있다([claude-base](../memory/claude-base.md) §세션 컨텍스트 규율) |
| interview-me 신뢰도 % | 질문 전 의도 가설과 신뢰도 숫자를 매번 적는다 | `grilling`에 넣으면 vendor 사본 오버라이드 비용이 생긴다. 승인 응답 판별만 가져왔다 |
| pstack `poteto-mode` · 원칙 스킬 23개 | 상시 라우터 모드, 원칙 상주 | 기존 판정 유지([pstack 검토](pstack-harness-adoption-review.md) §그대로 도입하지 않을 부분) |

## 후속 후보

수요·효과가 확인되면 착수한다. 지금은 지시를 늘리지 않는다.

| 후보 | 내용 | 연결 | 북극성 |
|---|---|---|---|
| 스킬 라우팅 eval | Osmani [evals](https://github.com/addyosmani/agent-skills/blob/aeac41d/evals/README.md) Tier 2 — description 쌍의 어휘 유사도로 충돌을, 발동/비발동 케이스로 누락을 결정적으로 잡는다. 모델 호출 `/ad:*` description에 적용 | [행동 평가 가이드](harness-behavior-evaluation.md)는 실제 산출물 비교라 비싸다. Tier 2는 CI에 올릴 수 있는 앞단 | 1·3 |
| description "언제" 문구 재작성 | Osmani [skill-anatomy](https://github.com/addyosmani/agent-skills/blob/aeac41d/docs/skill-anatomy.md) — description은 무엇 + "Use when" 조건, 절차 요약은 넣지 않는다 | 라우팅 eval 결과로 우선순위를 정한다. [스킬 작성 원칙](../policies/skill-authoring-principles.md) §1 | 3 |
| 관측성 runbook 3줄 | Osmani [observability-checklist](https://github.com/addyosmani/agent-skills/blob/aeac41d/references/observability-checklist.md) — 알람마다 runbook 최소 3줄(의미·첫 조회·에스컬레이션) | 서비스 하네스 `RUNBOOK.md` 템플릿 | 4·6 |
| 롤백 트리거 임계 수치화 | Osmani shipping-and-launch의 rollout 임계표(진행·보류·롤백) | 서비스별 에러율·지연 수치를 카탈로그·`RUNBOOK.md`에 | 5 |
| 실수 → 스킬 수정 회고 | pstack [reflect](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/reflect/SKILL.md)(세 관점 회고 → 채택·기각·백로그, 검사로 바꿀 수 있는 것은 구조 변경으로) + 영상 [12:14] "에이전트가 실수하면 스킬을 고친다" | `/ad:harness-optimize`의 입력으로 세션 실수 사례를 받아 분류 | 1·6 |
