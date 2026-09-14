# DEV2 pstack 지침·블록의 하네스 적용 초안

검토일: 2026-09-14. B01–B10 적용 완료: [실제 반영 내역·검증 결과](pstack-harness-implementation.md). 아래 문안과 줄 번호는 적용 전 제안 기록으로 보존한다.

[전체 스킬·컨셉 검토](pstack-harness-adoption-review.md)의 후속이다. 원본은 같은 [pstack 고정 커밋](https://github.com/cursor/plugins/tree/5bf2b1544db739998121a306340631963c2ff3de/pstack)을 사용한다. 아래 블록은 원문 인용이 아니라 팀 환경에 맞춘 한국어 번안·설계 제안이다. 현재 작업 트리와 비교했으며 줄 번호는 이번 검토 시점 기준이다.

## 적용 판단

**새 스킬을 추가하지 않고도 8개 지침 블록을 기존 파일에 흡수할 수 있다.** 나머지 2개는 서비스 실행 계약이나 검사 도구를 실제로 만들어야 효과가 생긴다. 기존 문구를 대체할 수 있으면 대체하고, 동일 규칙의 복제는 피한다.

| 번호 | 블록 | 현재 위치·반영 형태 | 우선순위 |
|---|---|---|---|
| B01 | 스킬 효과는 관찰된 행동으로 검증 | `skill-authoring-principles` §3의 검증법 대체 | 우선 |
| B02 | 삭제 테스트의 조건 고정 | `harness-governance-policy` §변경 통제의 1회 비교 규칙 대체 | 우선 |
| B03 | 완료 보고에 실제 증거 연결 | DoD의 테스트 통과 문구 대체, PR 템플릿에 결과 요약 | 우선 |
| B04 | 안전성을 지탱하는 가정 입증 | `code-review` §검증 순서에 조건부 블록 | 우선 |
| B05 | 작성 의도와 현재 동작의 근거 분리 | work-prep 노트의 판단·미확정 표현 보완 | 우선 |
| B06 | 회고를 문장 추가·도구화·기각으로 분기 | `harness-optimize` §제약 감사의 권장 조치 판정 보완 | 우선 |
| B07 | 반복 실패의 공통 전제 재검토 | mattpocock 팀 오버라이드의 디버깅 보완 | 선택 |
| B08 | 인계 증거가 적용되는 revision·작업 상태 | 기존 completion evidence·계획 진행 기록 확장 | 선택 |
| B09 | 실행 검증의 생명주기와 오류 분리 | 서비스 하네스용 새 계약 템플릿 후보 | 구현 동반 |
| B10 | 도구화의 완료 기준은 재실행 결과 | 제약 감사의 도구화 후보 acceptance | 구현 동반 |

B01·B02는 잘못된 검증 대리 지표를 바꾸는 작업이다. B03~B08은 모든 요청에 붙이는 전역 지시가 아니라 해당 스킬이 이미 호출된 상황에서 사용하는 작은 블록이다. B09·B10을 문장만 추가하고 완료로 처리하지 않는다.

## B01. 원칙 이름의 재등장 대신 실제 행동 확인

**현재:** [스킬 작성 원칙](../policies/skill-authoring-principles.md) §3, 49행은 다음을 검증법으로 둔다.

> 에이전트 reasoning에 그 단어가 다시 나타나면 작동하는 것. 안 나타나면 더 강한 단어로 교체

단어를 언급한 것과 행동이 바뀐 것은 다르다. 내부 reasoning을 관찰 대상으로 삼는 것도 런타임 간 재현이 어렵다. pstack `eval`은 실제 파일 읽기·결과로 확인한다. [원본 §Steps 6–7](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/eval.md).

**대체 문안 — 1줄:**

```markdown
- 검증법: 대표 요청에서 관찰 가능한 도구 호출·참조 파일·산출물이 목표 행동으로 바뀌었는지 확인한다. 원칙 이름의 재등장이나 적용했다는 자기 보고는 검증 근거로 세지 않는다.
```

효과 확인: 원칙을 말만 하고 기존 행동을 반복한 결과와, 원칙을 언급하지 않아도 올바른 결과를 만든 경우를 구별한다. 도구 호출 기록이 없는 런타임은 산출물로 확인하고 확인할 수 없는 과정은 미확인으로 남긴다. 숨겨진 사고 과정의 수집을 요구하지 않는다.

## B02. 삭제 테스트를 한 번의 동일 출력으로 확정하지 않기

**현재:** [하네스 거버넌스](../policies/harness-governance-policy.md) §변경 통제, 49행은 “변경 전후 해당 스킬 1회 실행 비교, 같으면 확정”을 요구한다. [제약 감사](../.claude/commands/ad/harness-optimize.md) 175행과 [스킬 작성 원칙](../policies/skill-authoring-principles.md) 61행에도 비슷한 설명이 있다.

한 번 같았다는 사실은 규칙이 불필요하다는 충분한 근거가 아니다. 희귀하지만 중요한 분기를 다루던 문장일 수 있다. pstack의 블라인드 평가에서 조건 고정과 평가 대상에게 메타정보를 주지 않는 부분을 가져온다. [원본 §Non-negotiables / Frame / Set up](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/eval.md).

**SoT 대체 문안 — 거버넌스에만 본문 유지:**

```markdown
- 삭제·재표현 전후에 같은 대표 요청, 저장소 상태, 모델·설정·예산을 사용한다. 변경한 규칙이 발동하는 사례를 포함한다.
- 후보에게 평가 대상이라는 정보와 상대 후보를 노출하지 않는다. 중립 라벨의 결과를 같은 판정 기준으로 비교한다.
- 필수 행동·위반·산출물·비용을 대조한다. 결과 변동이 결론에 영향을 주면 반복 실행하고, 단일 실행의 일치만으로 규칙이 무효라고 확정하지 않는다.
```

다른 두 파일에는 이 SoT로 연결하는 짧은 참조만 둔다. 기존 정책·invariant를 삭제하는 승인 조건은 그대로 유지한다. 이 블록은 평가 프로토콜이며 자동 evaluator가 생겼다는 뜻은 아니다.

## B03. 완료 체크박스를 증거 포인터와 연결

**현재:** [DoD](../templates/dod-checklist.md) 9행은 “코드 변경 완료 및 테스트 통과”, [PR 템플릿](../templates/pr-template.md) 13행은 “테스트 포함/통과”다. [work-prep 템플릿](../docs/sprint/work-prep-note-template.md)에는 목적·방법·결과·판단·근거 위치가 이미 있으므로 새 검증표를 하나 더 만들 필요는 없다.

pstack에서 추가할 부분은 실제 산출물을 확인하고, 관찰할 수 없었던 것을 통과로 보고하지 않는 기준이다. [원본 Prove It Works](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-prove-it-works/SKILL.md).

**DoD 해당 체크박스 대체:**

```markdown
- [ ] 코드 변경 완료와 필수 테스트 통과를 확인했고, 해당 Task의 완료 조건에 대해 검증 대상·실행 방법·기대값·관찰 결과·근거 위치를 연결했다.
```

**PR의 기존 테스트 체크박스 뒤에 둘 결과 블록:**

```markdown
### 검증 결과
- 대상·환경: {revision 또는 산출물, 실행 환경}
- 실행·기대값: {명령/사용 경로와 사전에 정한 기대 결과}
- 관찰·근거: {실제 결과와 로그·파일·화면 등 근거 위치}
- 확인하지 못한 범위: {원인과 다음 검증; 없으면 생략}
```

동일 결과가 work-prep/repository evidence에 있으면 PR에는 링크와 한 줄 결과만 둔다. 수정 코드의 결과를 검증했다는 것과 배포 후 동작을 확인했다는 것을 구별한다. 내부 개발·별도 QA·배포 Task를 합치지 않으며, 문서 변경에는 문서의 링크·내용·생성 결과가 실제 산출물이다.

## B04. 리뷰의 핵심 안전 가정을 작은 검사로 확인

**현재:** [코드 리뷰](../.claude/commands/ad/code-review.md) §검증 순서와 §APPROVE 승인 조건은 이미 조사와 통과 근거를 요구한다. 새로운 영향 목록을 만들기보다 “어떤 사실 덕분에 안전하다고 판단했는가”를 명확하게 한다. [원본 blast-radius §How sure are you / Steps 2–5](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/blast-radius/SKILL.md).

**§검증 순서에 둘 조건부 블록:**

```markdown
공유 상태, 비동기 순서, 외부 라이브러리, 직렬화·외부 계약의 가정이 안전성을 좌우하면:
- 핵심 가정을 한 문장으로 적고, 실제 고정 버전·호출 경로·소비자를 확인한다.
- 가장 작은 재실행 가능한 검사로 그 가정을 확인한다. 정적 근거만 있으면 실행 검증으로 보고하지 않는다.
- 결과에는 가정, 근거 수준(정적 확인/실행 확인/미확인), 관찰값과 증거 위치를 남긴다.
```

기존 미리보기의 해당 축 통과 근거에 붙이고 별도 전체 위험표는 만들지 않는다. 이 블록이 실행 환경 없는 리뷰를 자동으로 차단하거나 모든 PR에 E2E를 요구하지는 않는다. 안전 판정에 필요한 근거가 부족하면 기존 미확인 축·이벤트 선택 규칙으로 처리한다. DB·운영 쓰기 권한도 확대하지 않는다.

## B05. 코드의 현재 동작으로 작성 의도를 설명하지 않기

**현재:** [work-prep 본문 템플릿](../docs/sprint/work-prep-note-template.md) 110행은 `확정/유력 가설`, 160행은 `미확정 질문`을 이미 갖는다. 여기에 근거의 종류와 검색 공백을 명시하면 된다. pstack의 다섯 등급을 별도 enum으로 복제할 필요는 없다. [원본 why §Confidence Tiers / When Evidence Is Missing](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/why/references/epistemics.md).

**본문 템플릿의 기록 기준에 둘 블록:**

```markdown
- 작성 의도·과거 결정의 확정 근거는 당시 PR·티켓·결정 기록 등 명시적 기록에 연결한다. 현재 코드는 동작의 근거로 사용한다.
- 여러 정황에서 도출한 결론은 추론임을 밝히고, 근거와 결론 사이의 연결을 짧게 적는다.
- 이유를 못 찾으면 조사한 기록·범위와 남은 질문을 `미확정 질문`에 남긴다. 미검색·접근 불가와 검색했으나 미발견을 구분한다.
```

중요 주장에만 적용한다. 문장마다 등급 태그를 붙이거나 검색 전문을 위키 첫 화면에 넣지 않는다. `relation_status`는 노트 간 관계의 상태이므로 주장 확신도 용도로 재사용하지 않는다.

## B06. 회고의 결과를 자동으로 새 지침으로 만들지 않기

**현재:** [제약 감사](../.claude/commands/ad/harness-optimize.md) 173행에는 유지/완화/제거/도구화/근거 부착이 있다. 북극성에도 지시보다 검사가 우선한다는 원칙이 있다. 부족한 부분은 실패 원인을 어느 변경으로 보낼지 판정하는 짧은 기준이다. [원본 reflect §Structural enforcement check](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/reflect/SKILL.md), [종합 필터](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/reflect/references/synthesizer.md).

**권장 조치 판정 뒤에 둘 블록:**

```markdown
- 기존 규칙이 있는데 호출되지 않았다면 description·진입 경로를, 읽었는데 지켜지지 않았다면 실행 환경·검증 신호를 먼저 점검한다.
- 반복 오류를 lint·schema·권한·실행 검사로 잡을 수 있으면 도구화 후보로 보낸다. 더 강한 경고 문장을 추가하는 것으로 닫지 않는다.
- 기존 SoT가 틀렸다면 그곳을 수정 후보로 삼는다. 재발 조건이나 다음 판단의 변화가 불명확한 일회성 관찰은 새 규칙으로 승격하지 않는다.
```

“규칙을 읽었음”은 관찰 가능한 참조 기록이 있을 때만 판정한다. 사용자별 취향을 팀 규칙으로 일반화하지 않는다. 채택·기각·백로그는 기존 audit baseline에 남기고 외부 티켓을 자동 생성하지 않는다.

관련 작은 대체 후보: [서비스 AGENTS 템플릿](../templates/service-harness/AGENTS.md.tmpl) 85행의 “장애, 운영 이슈, 위험 포인트를 발견할 때마다 여기에 추가”를 다음으로 바꿀 수 있다.

```markdown
> 코드·검사로 표현하기 어려운 외부 제약과 결정 이유만 참조 링크로 남긴다. 사건 이력은 운영 노트에 두고, 반복 오류는 하네스 감사의 도구화 후보로 보낸다.
```

사건 누적으로 서비스 진입점이 계속 커지는 것을 막는 대체다. B06의 판정 절차 전문을 서비스마다 복제하지 않는다.

## B07. 같은 전제에서 실패한 수정의 반복 끊기

**현재:** [diagnosing-bugs](../vendor/mattpocock/diagnosing-bugs/SKILL.md) §Phase 3–5는 이미 복수 가설·반증 가능한 예측·한 변수씩 계측·원래 재현 재실행을 요구한다. 이를 다시 추가할 필요는 없다. 새로 얻을 수 있는 것은 여러 수정이 공유한 전제를 재검토하는 분기다. [원본 Attack the Premise](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-attack-the-premise/SKILL.md).

**[mattpocock 팀 오버라이드](../policies/overrides/mattpocock.md)의 디버깅 보완 후보:**

```markdown
같은 전제에 기대는 서로 다른 수정이 같은 재현 검사에서 반복 실패하면, 다음 수정 전에 공통 전제를 한 문장으로 적는다.
편중·누수·경합 문제라면 작업자·세션·인스턴스별 상태나 자원 분포를 측정하고, 특정 대상에 역할을 배정하는 구조를 확인한다.
관찰이 예측과 다르면 전제를 바꾼다. 한 원인의 임계값·재시도 횟수만 계속 조정하지 않는다.
```

원본의 actor별 census는 자원 편중 문제에 적합하므로 모든 버그에 강제하지 않는다. 횟수만으로 사용자에게 질문하거나 작업을 중단하는 규칙도 아니다. vendor 원본을 직접 고쳐 향후 동기화 부담을 늘리지 않는다.

## B08. 인계 시 완료 주장과 현재 작업 상태 연결

**현재:** [completion evidence](../configs/discord-agent-profiles.yaml) 204–211행은 변경 산출물·verification·남은 위험·승인 필요를 갖는다. [plan-run](../.claude/commands/ad/plan-run.md)은 진행 기록과 evidence를 갖고, [handoff 엔진](../vendor/mattpocock/handoff/SKILL.md)은 기존 산출물 참조를 요구한다.

추가할 것은 새 일지가 아니라 검증 증거가 어느 작업 상태에 대해 유효한지다. [원본 session-pickup](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/session-pickup.md), [shipping §판정 대상 재확인](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/shipping.md), [show-me-your-work](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/show-me-your-work/SKILL.md).

**기존 verification 값과 진행 기록에 넣을 공통 내용:**

```markdown
- 검증 대상: {repo/worktree, base·head revision, 미커밋 변경 유무와 해당 diff/산출물 포인터}
- 검증 증거: {실행 시점·환경·실제 결과를 담은 기존 evidence 링크}
- 현재와의 차이: {검증 이후 변경된 코드·설정·데이터, 없으면 없음}
- 다음 행동: {완료한 작업을 반복하지 않고 이어갈 첫 단계}
```

장시간 작업에서 중요한 채택·기각·전환만 기존 진행 기록에 `판단 → 이유 → 증거 → 결과`로 남긴다. 모든 명령을 새 TSV에 기록하지 않는다. 코드 작업이 아니면 revision 대신 대상 산출물의 버전·digest 등 적합한 식별자를 쓴다.

`head SHA`가 같아도 미커밋 수정과 환경이 다르면 같은 검증 대상이 아니다. `patch-id`가 같아도 런타임 증거를 자동 승계하지 않는다. 초기 적용은 기존 `verification` 필드의 내용 규격으로 두고, YAML `required_fields`를 늘리는 schema 변경은 실제 소비자와 호환성을 확인한 뒤 수행한다.

## B09. 서비스 실행 검증 계약과 오류 분류

**현재:** [카탈로그 검증 규격](../catalog/README.md)은 빠른 build/test/lint/typecheck 루프다. [서비스 AGENTS 템플릿](../templates/service-harness/AGENTS.md.tmpl)에는 배포 후 smoke test 자리만 있다. 배포 후 검사를 구현 중 검증으로 이름만 바꿔 사용하면 안 된다.

**신규 후보:** `templates/service-harness/VERIFICATION.md.tmpl`. 아직 생성하지 않았다. 공통 형식만 team2가 소유하고, 실제 명령·기능 경로는 서비스 repo가 소유한다. [생성 원본](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/create-verification-skill/SKILL.md), [유지보수 원본](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/maintain-verification-skill/SKILL.md).

**템플릿의 핵심 블록:**

```markdown
## 실행과 대상 확인
{실제 시작 명령, 준비 완료 신호, revision·인스턴스·인증 확인, 격리 방법}
## 기능별 검증
{기능 / 사용자 진입 경로 / 입력·조작 / 기대 상태 / 관찰할 부작용}
- 조작이 실패하면 대상 상태를 다시 확인한다. 프로세스가 살아 있어도 화면·세션이 막혔으면 알려진 초기 상태로 되돌린 뒤 재시도한다.
## 증거와 정리
{관찰 결과 저장 위치, 자신이 시작한 프로세스·임시 상태 정리, 정리 후 증거 보존 확인}
## 계약 유지보수
- 설명이 틀렸으면 문서 드리프트, 동작은 맞지만 실행 도구가 못 따라가면 도구 공백, 기대 동작 자체가 깨졌으면 제품 결함으로 구분한다.
- 문서·도구 보정 뒤 같은 경로를 다시 실행한다. 제품 결함을 기대값 변경으로 덮지 않는다.
```

생성 완료 기준은 placeholders가 사라졌다는 것만이 아니다. 새 세션에서 대표 기능 하나를 실행·관찰·정리하고 증거를 다시 열 수 있어야 한다. 제어할 수 없는 상태는 필요한 권한·데이터·환경과 시도한 경로를 기록한다. CLI/API/라이브러리에 화면 캡처를 강제하지 않는다. 인증·운영 환경·부작용이 있는 검증은 기존 권한 범위에서 실행한다.

## B10. 도구화 완료를 재실행 가능한 결과로 판정

**현재:** 제약 감사는 도구화 후보를 낼 수 있지만, 어떤 결과면 도구화가 끝난 것인지 공통 판정이 구체적이지 않다. 원칙을 하나 더 선언하기보다 실제 도구 작업의 acceptance로 사용한다. [원본 Build the Lever](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-build-the-lever/SKILL.md), [멱등성 원칙](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-make-operations-idempotent/SKILL.md).

**도구화 후보를 계획·티켓에 넘길 때 사용할 블록:**

```markdown
- 대표 입력에서 기대 결과 또는 잡아야 할 실패를 먼저 고정한다. 기존 도구가 같은 판정을 제공하면 재사용한다.
- 최소 검사·변환기를 만들고 실제 입력에서 실행해 결과를 비교한다. 호출법과 결과 위치를 함께 남긴다.
- 상태를 쓰는 도구는 재실행·부분 실행 뒤 재개 시 중복·누락·다른 작업 덮어쓰기가 없는지 확인한다.
- dry-run은 이름만 신뢰하지 않고 파일·네트워크·외부 상태의 실제 변경 여부를 확인한다.
```

마지막 항목은 [검증 생성 스킬의 Evidence 절](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/create-verification-skill/SKILL.md)에서 가져온다. 실효성이 드러나는 적용 예는 문서 일괄 갱신, 링크 projection 생성, 중복 접수 방지, 상태 기록 도구다. 단일 문구 수정에 generator를 만들지 않는다. 외부 쓰기를 두 번 실행해 안전성을 시험하지 않고 fixture·격리된 테스트 환경에서 검증한다.

## 본문까지 비교한 뒤 추가하지 않기로 한 블록

| pstack 내용 | 현재 하네스에 이미 있는 근거 | 이번 판단 |
|---|---|---|
| caller 사용 예·타입·대안 인터페이스 비교 | [codebase-design의 Design It Twice](../vendor/mattpocock/codebase-design/DESIGN-IT-TWICE.md)에 interface, usage example, 숨기는 구현, 의존 전략, trade-off와 비교 절차 존재 | 새 `architect` 블록 불필요. 기존 엔진의 해당 참조를 사용할 문제인지 판정 |
| 복수 가설·반증·한 변수 계측·원래 재현 재실행 | [diagnosing-bugs](../vendor/mattpocock/diagnosing-bugs/SKILL.md) Phase 3–6 | 중복 추가 제외. B07의 공통 전제 재검토만 차이 |
| 성능 baseline을 먼저 측정 | 같은 diagnosing-bugs의 Perf branch | 원칙 문장 추가 제외. 반복 최적화가 실제 필요할 때만 고정 workload·측정 오차·회귀 조건을 실험에 적용 |
| 단계별 종료 조건·증거 없는 완료 금지 | [plan-run](../.claude/commands/ad/plan-run.md)의 착수·종료 전이 | 중복 추가 제외. B08로 증거의 유효 범위만 보완 |
| 통과·기각에도 근거 요구 | [code-review](../.claude/commands/ad/code-review.md)의 미확인 축·강등된 질의·교차 검증 | 기존 규칙 유지. B04로 고위험 가정의 실행 근거만 구체화 |
| 위임마다 새 역할·모델을 지정하고 복수 리뷰 강제 | 팀 AGENTS 모델 라우팅과 기존 교차 모델 리뷰 | pstack의 고정 모델·agent 개수·매번 재평가 의례 제외 |
| 내부 API의 호출자를 모두 옮기고 구 API 제거 | 팀의 legacy adapter·소비자 계약·배포 경계가 더 중요 | 모든 migration에 일괄 삭제 지침 추가 제외 |

## 적용 시 편집 범위

- 전역 `AGENTS.md`·`CLAUDE.md`에는 위 블록을 추가하지 않는다. 실제 소비 지점이나 하나의 SoT에만 둔다.
- `.codex/skills/ad-*/SKILL.md`는 얇은 alias로 유지한다. source command의 본문 변경을 alias에 복제하지 않는다.
- vendor 원문은 직접 수정하지 않는다. 필요한 차이만 기존 팀 오버라이드에 두고, 독립적으로 재사용될 때만 참조 파일로 분리한다.
- 문구 변경의 수용 기준은 이 문서의 타당성만이 아니라 B01·B02의 관찰 결과다. 서비스 계약·도구화는 B09·B10의 실제 실행까지 확인한다.

이 초안 이후 사용자의 전체 적용 요청에 따라 정책·템플릿·source command·설정과 검증 도구를 반영했다. 최종 범위와 한계는 [적용 기록](pstack-harness-implementation.md)을 따른다.
