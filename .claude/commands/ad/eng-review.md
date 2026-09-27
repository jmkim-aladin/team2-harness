---
description: 설계 검증(eng review) — 구현 전 계획의 스코프·아키텍처·코드 품질·테스트·성능을 이슈 단위로 판정. "설계 리뷰", "계획 검토해줘", "구현 전에 봐줘" 류에
---

# 설계 검증 (eng-review)

구현 전에 계획을 잠근다. 스코프 → 아키텍처 → 코드 품질 → 테스트 → 성능 순으로 이슈를 **하나씩** 사용자와 판정하고, 판정 결과를 대상 노트에 남긴다. 계획을 고치는 주체는 사용자 판정이다 — 리뷰어는 근거와 추천안을 낸다.

- 플로우 위치: `/ad:work-prep` 뒤 · `/ad:implement` 앞, 또는 `/ad:plan` 계획 노트 검토. 기본: 1일 이상 작업이거나 아키텍처·DB·공통 서비스 경계가 걸릴 때
- 출처: gstack `plan-eng-review` v1.60.1.0 번안 ([NOTICE](../../../docs/eng-review/NOTICE.md)). 기존 저장소 구조 분석은 `/ad:architecture-analysis`, PR diff 판정은 `/ad:code-review`

## 1. 검토 대상 확정

- 인자·대화에서 대상을 식별한다: 티켓 ID(→ YouTrack Feature 5W1H 본문 + `$LOCAL_WIKI_PATH/wiki/processes/tickets/dev2-{nnnn}.md`) / 계획 노트 경로 / 브랜치 diff / 파일·디렉토리
- 조회로 확정되면 묻지 않는다. 후보가 둘 이상일 때만 추천안과 함께 질문한다
- spec(5W1H 본문·계획 노트)이 없으면 `/ad:grill` 정렬을 먼저 권한다. 사용자가 생략하면 대화에 준 내용을 spec으로 진행
- 완료: 검토 대상 문서와 코드 범위가 한 줄로 확정됨

## 2. 입력 수집

- 서비스 프로파일 `catalog/{service}.yaml` — `architecture`·`dependencies`·`risk`·`build`·`verification`
- 계획이 건드리는 경계별 SoT: 공통 서비스(로그인·권한·회원 식별·결제·정산·구독·공유 API) → [common-service-policy.md](../../../policies/common-service-policy.md) + [registry.yaml](../../../catalog/common-services/registry.yaml) / 신규 앱 도메인 → [internal-domain-policy.md](../../../policies/internal-domain-policy.md) / 기술 스택 → [engineering-policy.md](../../../policies/engineering-policy.md) §기술 스택 원칙 / DB·SP 변경 → 별도 승인 대상으로 표시
- 과거 결정: vault decisions([docs/agents/domain.md](../../../docs/agents/domain.md) 배치)와 gbrain 검색([docs/gbrain-config.md](../../../docs/gbrain-config.md)). 이 계획과 모순되는 결정이 있으면 이슈로 올린다
- 브랜치가 있으면 git log에서 이전 리뷰 라운드 흔적(리뷰 반영 커밋·revert)을 찾는다. 같은 영역을 건드리면 그곳을 더 세게 본다
- 완료: 계획이 건드리는 서비스·경계·정책 목록 확정

## 3. Step 0 — 스코프 챌린지

리뷰 섹션에 들어가기 전에 답한다.

1. **이미 있는 것** — 하위 문제를 기존 코드·흐름이 이미 푸는가? 병렬 구조를 새로 짓는 대신 기존 출력을 재사용할 수 있나
2. **최소 변경** — 목표를 달성하는 최소 변경 집합. 핵심을 막지 않고 미룰 수 있는 작업을 표시한다
3. **복잡도** — 8파일 초과 또는 신규 클래스·서비스 2개 초과면 smell. 더 적은 부품으로 같은 목표가 되는지 따진다
4. **built-in 검색** — 도입하는 패턴·인프라·동시성 방식마다 프레임워크 내장 여부, 현행 모범 사례, 알려진 함정을 WebSearch로 확인한다. 검색이 안 되면 "검색 불가 — 학습 지식만"이라고 적는다. 내장이 있는데 자체 구현하면 스코프 축소 기회로 올린다
5. **완결성** — 지름길이 사람 시간은 아끼지만 AI 구현 시간은 몇 분만 아낀다면 완전판(테스트·엣지·에러 경로 포함)을 권한다. 단 Task ≤ 1일 규칙 안에서 — 넘치면 분할을 제안한다
6. **단계 분리** — 검증(테스트/QA 시너지팀)·배포·운영 반영 단계가 계획에 있는가 ([ticket-guide.md](../../../docs/sprint/ticket-guide.md) 2-2항). 빠졌으면 "범위 밖"에 명시해 조용히 사라지지 않게 한다

복잡도(3)가 걸리면 섹션 리뷰 전에 멈춘다: 과잉 부분을 지목하고 최소판을 제안한 뒤 줄일지 그대로 갈지 질문하고 답을 기다린다. 걸리지 않으면 Step 0 결과를 제시하고 섹션 리뷰로 간다.

사용자가 스코프를 판정하면 그 판정으로 끝까지 간다 — 뒤 섹션에서 다시 줄이자고 재론하지 않고, 합의된 구성요소를 조용히 빼지 않는다.

- 완료: 스코프 합의 한 줄

## 4. 섹션 리뷰

Step 0 합의 후 [docs/eng-review/review-sections.md](../../../docs/eng-review/review-sections.md)를 읽고 그 점검표로 수행한다 — 기억으로 하지 않는다. 순서는 아키텍처 → 코드 품질 → 테스트 → 성능, 섹션당 상위 8개 이슈.

**질문 규율**

- 이슈 하나 = 질문 하나. 묶지 않는다. 번호+선택지 문자로 라벨(`3A`, `3B`)
- 선택지 2~3개(합리적이면 "그대로 둔다" 포함), 각 한 줄: 노력·위험·유지보수 부담
- 추천안과 이유 한 문장 — 아래 판단 기준 중 어디에 근거하는지 밝힌다
- 선택지가 커버리지 차이(테스트 더/덜, 에러 처리 완전/부분)면 선택지마다 `완결성: N/10`. 종류 차이(서로 다른 구조)면 점수 없이 "종류가 달라 완결성 점수 없음"
- 이슈 없는 섹션은 "이슈 없음" 한 줄로 넘어간다. 수정이 뻔해 보여도 사용자 승인 전에는 계획에 반영하지 않는다
- 사용자가 답 없이 넘어가면 미결로 기록한다. 기본값으로 조용히 정하지 않는다
- 사실은 조회로 해소하고 결정만 묻는다. Codex 호스트에서는 짧은 직접 질문 ([AGENTS.md](../../../AGENTS.md) §도구 대응)

**판단 기준**

- DRY 위반은 적극 지적한다 / 테스트는 모자람보다 넘치는 쪽 / "적당히 설계" — 취약한 땜질도 섣부른 추상화도 아닌 / 엣지 케이스는 더 다루는 쪽 / 영리함보다 명시성 / 변경을 깔끔히 표현하는 최소 diff, 단 기반이 망가졌으면 "갈아엎고 이렇게"
- blast radius — 최악의 경우와 영향 받는 시스템·사람 수 / boring by default — 혁신 토큰은 셋뿐, 나머지는 검증된 기술 / strangler fig·canary — 점진이 기본 (레거시 .NET·SP 경계는 [engineering-policy.md](../../../policies/engineering-policy.md) §레거시 서비스) / reversibility — feature flag·단계 배포로 틀렸을 때 비용을 낮춘다 / 새벽 3시의 지친 사람 기준으로 설계 / essential vs accidental complexity — "진짜 문제인가, 우리가 만든 문제인가" / make the change easy, then make the easy change — 구조 변경과 동작 변경을 한 번에 섞지 않는다 / Conway's law

컨텍스트가 압박되면 우선순위: Step 0 > 테스트 다이어그램 > 추천안 > 나머지. Step 0과 테스트 다이어그램은 생략하지 않는다.

## 5. 교차 모델 의견 (outside voice)

기본: 섹션 리뷰가 끝나면 다른 모델로 독립 의견을 받는다. 단 Task 1개(≤1일) 규모이거나 사용자가 생략을 원하면 생략.

```bash
# Claude Code 호스트 → Codex. -C 는 검토 대상 repo — 하네스 cwd에서 돌리면 하네스를 본다
codex exec -s read-only -C "{대상 repo}" "$(cat "$PROMPT_FILE")" \
  -c 'model_reasoning_effort="high"' < /dev/null        # timeout 300000

# Codex 호스트 → Claude Code
(cd "{대상 repo}" && claude -p "$(cat "$PROMPT_FILE")" \
  --model opus --allowedTools Read Grep Glob) < /dev/null
```

CLI가 없거나 실패·시간 초과면 새 컨텍스트 서브에이전트(Agent)에 같은 프롬프트를 준다. 프롬프트(계획이 30KB를 넘으면 앞 30KB + "잘림" 표기):

```
스킬 정의 파일(~/.codex/skills, ~/.claude, .claude/commands, .agents)은 읽지 않는다. 저장소 코드와 아래 계획만 본다.
너는 이미 여러 섹션 리뷰를 거친 개발 계획을 보는 가차 없는 기술 리뷰어다. 그 리뷰를 반복하지 말고 놓친 것을 찾는다:
살아남은 논리 공백과 숨은 가정, 과잉 복잡도(근본적으로 더 단순한 접근), 당연시한 실현 가능성 위험,
빠진 의존성·순서 문제, 전략 오판(이걸 만드는 게 맞나). 직설적으로, 짧게, 칭찬 없이 문제만.

계획:
<계획 본문>
```

- 출력은 요약하지 않고 원문 그대로 제시한 뒤, 섹션 리뷰와 부딪히는 지점을 `교차 모델 긴장: [주제] — 리뷰는 X, 외부 의견은 Y`로 중립 제시한다
- 외부 의견은 정보다. 긴장점마다 질문으로 사용자 판정(수용 / 유지 / 추가 조사 / 후속 Task)을 받는다. 두 모델이 합의해도 승인 없이 반영하지 않는다

## 6. 산출물과 기록

필수 산출 (대화에 제시):

- **범위 밖** — 검토했으나 미룬 작업 + 한 줄 이유
- **이미 있는 것** — 하위 문제를 푸는 기존 코드·흐름과 재사용 여부
- **실패 모드** — 테스트 다이어그램의 새 경로마다 현실적 운영 실패 하나: 테스트 유무 · 에러 처리 유무 · 사용자에게 보이는지. 셋 다 없으면 **critical gap**
- **구현 Task** — `T1 (P1) — {컴포넌트} — {명령형 제목}` / 근거: {섹션·이슈 번호} / 파일 / 검증: {명령}. P1 = 머지 차단, P2 = 같은 브랜치, P3 = 후속. 발견이 없는 섹션에서 Task를 지어내지 않는다
- **병렬화** — 독립 작업 흐름이 2개 이상이면 모듈 단위 의존 표 + lane(병렬/순차) + 같은 모듈을 건드리는 lane 충돌 경고. 아니면 "순차 구현"
- **미결 결정** — 답을 못 받은 질문 목록
- **완료 요약** — Step 0 판정 / 섹션별 이슈 수 / 테스트 gap 수 / critical gap 수 / 외부 의견 실행 여부

기록 위치 ([knowledge-base-policy.md](../../../policies/knowledge-base-policy.md) — 무엇을 일하나 = vault):

| 대상 | 기록 |
|---|---|
| 티켓 | 티켓 노트 기존 절에 반영 — 확정 결정 → `결정 패킷`, 미결 → `미확정 질문`, 구현 Task·테스트 gap → `Actions`, `완료 기록` 한 줄. 템플릿 SoT: [work-prep-note-template.md](../../../docs/sprint/work-prep-note-template.md), 120줄 목표 유지 — 다이어그램 전문은 대화에 둔다 |
| 계획 노트 (`/ad:plan` 산출) | 해당 노트에 `## 설계 검증 {YYYY-MM-DD}` 절 |
| 브랜치 diff·repo 문서 | 대화에 제시. 남길 가치가 있으면 knowledge-base-policy 결정 트리 |

- YouTrack Task 신설·변경이 필요하면 목록까지만 만들고 `/ad:ticket`으로 넘긴다 — 티켓 생성은 사용자 확인 대상이다
- 완료: 필수 산출 7종 제시 + (티켓·계획 대상이면) 노트 반영

## 다음 단계

- 스코프 합의 + P1 없음 → `/ad:implement` (단계 경계에서 `/clear` — 티켓 노트가 인계 매체)
- Task 구성이 바뀜 → `/ad:ticket`
- 결정 다수가 미결 → `/ad:grill`로 재정렬

ARGUMENTS: $ARGUMENTS
