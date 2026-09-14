# DEV2 pstack 스킬·컨셉의 하네스 적용 검토

검토일: 2026-09-14. 후속 블록 B01–B10 적용 완료: [반영 내역·검증 결과](pstack-harness-implementation.md). 아래 본문은 적용 전 검토와 후보 판정 기록이다.

후속: [기존 하네스에 넣을 지침·블록 문안과 대체 위치](pstack-harness-block-adoption-draft.md). 본문 수준 대조 결과, caller 사용 예와 복수 인터페이스 비교 등은 기존 엔진에 이미 있어 추가 대상에서 제외했다.

## 판단

**pstack 전체 설치보다 실행 검증 계약과 스킬 평가 방식을 기존 하네스에 흡수하는 편이 유리하다.** 팀은 이미 검증 루프, 짧은 컨텍스트, 아티팩트 기억, 도메인 모델링, 교차 모델 리뷰를 갖췄다. 차별점은 원칙의 수가 아니라, 실제 앱을 어떻게 검증하고 그 검증 수단을 어떻게 유지하는지에 있다.

우선순위는 다음과 같다. P1은 첫 적용 후보, P2는 특정 작업에서 시범 적용, P3은 수요가 생길 때 재검토한다. 우선순위와 적용 위치는 이 검토의 제안이며 확정 정책이 아니다.

| 순위 | 적용 후보 | 현재 대비 추가 가치 | 북극성 |
|---|---|---|---|
| P1 | 서비스 실행 검증 계약 + 기능 지도 + 유지보수 검사 | 빌드·테스트 명령에서 실제 사용자 동작·증거·정리까지 연결 | 1·4 |
| P1 | 스킬 변경의 블라인드 행동 평가 | 구조 lint와 문서 감사에 실제 행동 회귀 신호 추가 | 1·3 |
| P1 | 변경 안전성을 지탱하는 핵심 가정의 실행 입증 | 영향 목록에서 안전 판정의 근거를 실행 가능한 검사로 전환 | 1·5 |
| P2 | 중요한 판단 기록 + 재개 시 증거 유효성 확인 | 작업 내역보다 채택·기각 이유와 검증 대상 revision을 보존 | 4·6 |
| P2 | 설계 의도 조사에서 사실·추론·미확인 분리 | 현재 코드로 과거의 의도를 지어내는 오류 방지 | 4·6 |
| P2 | 사용 예·타입 선행 설계 + 같은 과제의 대안 비교 | 비용이 큰 설계 결정에서 첫 답에 고착되는 위험 감소 | 2 |
| P2 | 측정기를 고정한 성능 개선 루프 | 같은 조건에서 한 가설씩 개선·회귀 여부 판정 | 1 |
| P3 | Benny의 접수·재현·기존 수정 검증 분리 | 운영 자동화의 중복 작업과 오탐 억제 | 1·5 |

판정 기준은 [하네스 북극성](../policies/harness-north-star.md), [스킬 작성 원칙](../policies/skill-authoring-principles.md), [지시 강도·우선순위](../policies/instruction-precedence-policy.md)다. 특히 원칙을 더 많이 상주시킬 필요는 없다.

## 검토 범위와 근거

- 외부 원본: [cursor/plugins의 pstack](https://github.com/cursor/plugins/tree/5bf2b1544db739998121a306340631963c2ff3de/pstack). GitHub API로 확보한 커밋 `5bf2b1544db739998121a306340631963c2ff3de` 기준. [manifest](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/.cursor-plugin/plugin.json)의 버전은 `0.15.2`.
- 일반 스킬 47개: 작업 스킬 24개 + `principle-*` 23개. 별도로 Benny 자동화용 `SKILL.md` 3개. 총 50개 전수 검토.
- 컨셉: README, 가이드 10장, 라우터와 playbook 23개, agent 2종, 주요 references와 실행 보조 스크립트 구조.
- 로컬 비교: team2의 현재 작업 트리. 기존 미커밋 정책·카탈로그·리뷰 수정도 포함. 서비스 저장소 전수 실사나 실제 앱 구동은 수행하지 않았다.
- 이 문서는 하네스 설계 검토이므로 team2 `docs/`에 둔다. 서비스별 검증 구현은 해당 서비스 repo, 작업별 증거·진행은 기존 spec/위키의 거처를 따른다.

상위 README의 홍보 문구와 스킬·코드가 보장하는 범위를 구분했다. 원본의 모델 선택·명령·자동화 절차는 분석 대상이며 이번 세션에 적용하거나 실행하지 않았다.

## 컨셉을 팀 하네스와 비교

| pstack 컨셉 | 팀의 현재 기반 | 판정 |
|---|---|---|
| 적게 만들고 실제 동작으로 입증한 뒤 병렬화 | 북극성 1·2·3, 도메인 모델링, TDD, 교차 리뷰 | 방향 일치. 새 선언문 불필요 |
| `poteto-mode`가 작업을 분류하고 playbook·원칙 호출 | description 기반 라우팅, 상황별 `/ad:*`, 동사·엔진·자료 분리 | 라우터 추가 불필요. 현재 진입점 유지 |
| 짧은 이름의 원칙으로 행동 교정 | 기존 정책·엔진 어휘, 북극성 6개 | 필요한 사례만 기존 원칙의 예제로 흡수 |
| 재사용 가능한 앱 조작·검증 수단 | 카탈로그 `verification.loops` | 가장 큰 보완 가치. 실행 동작 계약 추가 |
| 같은 문제의 복수 해법과 독립 판정 | `prototype`, 설계 리뷰, 교차 모델 리뷰 | 어려운 결정에서 선택 사용. 모든 변경에 강제하지 않음 |
| 기능별 검증 수단의 드리프트를 실제 실행으로 판별 | 하네스 정적 감사·doctor, 서비스별 검증 명령 | 검증 문서의 기능별 실증 유지보수 보완 |
| 회고를 스킬·도구 수정으로 연결 | `harness-optimize`, 북극성의 지시→검사 원칙 | 행동 평가와 연결하는 부분 채택 |
| 장시간 실행의 종료 조건·판단 기록·검증 대상 고정 | `plan-run`의 milestone·evidence, context save/restore | 기존 상태 체계를 확장. 별도 운영 체계 중복 금지 |

외부 근거: [README](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/README.md), [원칙 가이드](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/docs/guide/08-principles.md). 로컬 근거: [스킬 작성 원칙](../policies/skill-authoring-principles.md), [작업 플로우](harness-guide.md), [계획 실행](../.claude/commands/ad/plan-run.md).

## 우선 적용 후보

### 1. 서비스 실행 검증 계약과 유지보수 루프

`create-verification-skill`은 저장소에서 실행 방법과 기존 테스트 도구를 조사해 Launch / Doctor / Drive / Evidence / Cleanup 계약을 만든다. 기능별 사용 경로를 지도에 적고, 최소 한 기능을 처음부터 끝까지 실행해 생성한 계약 자체를 입증한다. 정리 후에도 증거 파일이 남아 있는지 확인한다. `maintain-verification-skill`은 기능별 소스 조사와 실제 실행을 결합해 문서 드리프트, 검증 도구의 누락, 제품 결함을 분리한다. [생성 원본](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/create-verification-skill/SKILL.md), [유지보수 원본](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/maintain-verification-skill/SKILL.md).

팀에는 이미 [카탈로그 검증 규격](../catalog/README.md)의 `cwd`, `build`, `test`, `lint`, `typecheck`, `evidence`가 있다. DB·외부 인프라·브라우저가 필요한 검증은 기본 루프에서 제외하고 제약을 기록한다. 그러므로 기존 `verification`을 없는 것으로 취급하거나 전면 교체하면 안 된다.

**제안:** 빠른 검증 루프는 유지하고, 별도의 실행 검증 계약을 가리키는 포인터를 추가한다. 공통 형식은 `templates/service-harness/`, 실제 명령·기능 지도·도구는 서비스 repo 한 곳이 소유한다. `.cursor/skills/` 경로를 그대로 복사하지 않고 Claude/Codex가 같은 계약을 참조하게 한다.

| 계약 | 필요한 정보 | 판정 신호 |
|---|---|---|
| 실행 | 실제 시작 명령, revision, 환경, 테스트 데이터 | 준비 완료 신호와 실행 대상 식별 |
| 상태 확인 | 올바른 인스턴스·빌드·포트·인증 확인 | 다른 사용자/운영 인스턴스 오조작 방지 |
| 조작 | 기능별 진입 경로, 안정적인 selector·CLI·HTTP 입력 | 사용자가 거치는 경로로 기대 상태 도달 |
| 증거 | 명령·입력·출력·관찰값·실행 환경·revision | 성공 주장과 원본 증거 연결 |
| 정리 | 자신이 시작한 프로세스·임시 상태의 소유권 | 잔여 프로세스 없음, 증거 보존 |

완료 기준: 새 세션이 계약만 읽고 대표 기능 하나를 실행하고, 결과를 입증하고, 정리 후 증거를 다시 열 수 있음. 후속 유지보수에서는 지도에 등록한 모든 기능의 검증 여부 또는 접근 불가 사유를 반환함. 제품 회귀를 지도 수정으로 정상화하지 않음.

시범 대상은 카탈로그에 기존 실행 도구 근거가 있는 서비스에서 고른다. 예를 들어 [만권당](../catalog/max.yaml)의 Playwright smoke 경로나 [근태관리](../catalog/attendance.yaml)의 테스트 체계는 후보이나, 실제 착수 전 서비스 repo에서 동작과 안전한 환경을 재확인해야 한다. Windows/.NET Framework·외부 QA 의존 컴포넌트는 실행 불가를 명시하고 검증 완료로 세지 않는다.

### 2. 스킬 변경을 실제 과제로 비교

pstack의 `eval`은 후보가 평가 상황을 의식하지 않도록 같은 자연스러운 요청을 격리 환경에 주고, 중립 라벨로 결과를 비교한다. 스킬을 읽었다는 자기 보고 대신 실제 파일 읽기 기록과 산출물로 판단한다. `reflect`는 회고 항목을 채택·기각·백로그로 분류하고, 검사로 강제할 수 있는 것은 문장 추가보다 구조적 변경으로 돌린다. [평가 원본](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/eval.md), [회고 원본](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/reflect/SKILL.md).

팀도 이미 [스킬 스택 개선 계획](skill-stack-and-workflow-plan.md)에 대표 시나리오와 변경 전후 비교를 적었다. 다만 현재 [스킬 테스트](../tests/test_codex_skills.py)는 문구·크기·alias 참조 등 정적 계약을 검사한다. 조사 범위에서는 자연어 과제를 실행하고 전후 행동을 판정하는 evaluator를 확인하지 못했다. 따라서 새 평가 철학을 도입하기보다 기존 계획을 실행 도구로 완성하는 일이다.

**제안:** `harness-optimize`의 정적·사용 실적 감사 뒤에, 의미 있는 트리거·절차 변경만 행동 평가한다. 테스트 시나리오와 실행 도구를 `tests/`·`tools/`의 기존 패턴에 맞춰 둔다. 별도 사용자 스킬을 먼저 늘릴 필요는 없다.

첫 시나리오 후보:

- 읽기 전용 분석 요청에서 구현·게시로 넘어가지 않는지.
- 서비스 검증 명령이 없을 때 `npm test` 등을 만들어내지 않는지.
- 코드 리뷰에서 실제 PR revision과 다른 로컬 코드를 근거로 사용하지 않는지.
- API/공통 서비스 영향이 있는 변경에서 올바른 SoT를 읽는지.
- 검증 실행이 실패했을 때 완료로 보고하지 않는지.

완료 기준: 변경 전후에 같은 과제·환경·모델·예산을 사용하고, 필수 오류·완료율·불필요한 읽기·비용을 비교할 수 있음. 모델 변경 효과와 스킬 변경 효과를 한 번에 섞지 않음. 평가자의 판정과 기계 판정이 다르면 사람이 원본을 확인함. 단일 실행 승리를 일반화하지 않음.

외부 시스템은 fixture나 쓰기 권한 없는 어댑터로 대체한다. 활성 워크스페이스 밖의 개인 대화는 평가 자료로 수집하지 않는다. `reflect`의 외부 백로그 자동 등록은 팀에 그대로 적용하지 않는다.

### 3. 리뷰의 핵심 안전 가정을 실행으로 입증

`blast-radius`의 핵심은 호출자 목록을 길게 만드는 것이 아니다. “이 변경이 안전하려면 어떤 사실이 참이어야 하는가”를 좁히고, 실제 고정 버전 라이브러리·직렬화 형식·비동기 실행 순서·다른 언어의 소비자까지 살펴 그 사실을 실행한다. 실행하지 못한 가정은 미입증으로 표시한다. [원본](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/blast-radius/SKILL.md).

팀의 [가설 검증 순서](../policies/hypothesis-verification-order.md)와 [코드 리뷰](../.claude/commands/ad/code-review.md)는 이미 코드·데이터 조사, 교차 모델 대조, 미확인 축, 판정 근거를 요구한다. 새 `/ad:blast-radius` 진입점은 중복이다.

**제안:** 영향이 큰 가정에만 `안전 가정 → 실제 버전/경로 → 최소 실행 → 결과 → 남은 한계`를 기존 리뷰 엔진의 증거 규격으로 추가한다. 예: “새 캐시 제거 호출이 다른 사용자의 살아 있는 항목을 지우지 않는다”를 실제 저장소 구현을 부르는 작은 검사로 입증한다.

완료 기준: 위험을 좌우하는 가정마다 실행 증거 또는 미입증 사유가 남음. 정적 근거만 있는 것을 실행 검증으로 승격하지 않음. 리뷰를 위해 DB 쓰기나 운영 변경을 실행하지 않음. 기존 사용자 호출·게시 시점은 유지함.

## 선택 적용 후보

### 판단 기록과 증거의 유효 범위

`show-me-your-work`의 시간·결정·이유·증거·결과 구조는 장시간 작업에 유용하다. 작업마다 TSV를 만들기보다 기존 `plan-run` 진행 기록에 중요한 채택·기각 판단만 남긴다. `session-pickup`처럼 완료 작업을 다시 시작하지 않되, `repo / base SHA / head SHA / 환경 / 증거 위치 / 다음 행동`으로 현재 상태와 대조한다. [판단 기록](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/show-me-your-work/SKILL.md), [재개](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/session-pickup.md).

`shipping`은 판정 당시 head/base와 `git patch-id`를 기록하고 변경된 patch를 재검증한다. **팀 적용 시 patch-id는 코드 차이의 동일성 신호로만 사용한다.** patch가 같아도 base·의존성·환경 변경은 실행 결과를 바꿀 수 있으므로 런타임 증거까지 자동 승계하면 안 된다. [배포 playbook](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/shipping.md).

완료 기준: 다른 세션이 재개 지점과 유효한 검증 결과를 구분하고, 무효가 된 범위만 재검증할 수 있음. 중요 설계 결정은 [ADR 기준](../policies/engineering-policy.md)에 맞을 때만 ADR로 승격함.

현재 [handoff 프로파일](../configs/discord-agent-profiles.yaml)은 완료 evidence를, [오케스트레이션](../.claude/commands/ad/orchestration.md)은 role/model/effort/session을 다룬다. [아키텍처 보고서 템플릿](../templates/architecture-analysis/report.md)에는 source snapshot의 `commit_sha`도 있다. 새 공통 상태 저장소를 만들기보다 이 기존 계약에 검증 대상 revision을 연결하는 것이 작은 보완이다.

### 설계 의도의 증거 등급

`how`는 현재 동작, `why`는 결정 배경을 다룬다. 특히 `why`는 직접 기록·간접 지지·추론·가설·모름을 구분하고, 검색해도 못 찾은 경위도 보고한다. [인식론 참조](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/why/references/epistemics.md).

`work-prep` 및 분석·설명 엔진에 “코드는 동작의 근거이고 작성 의도의 직접 증거는 아니다”와 미확인 범위 기록을 흡수한다. GitHub `gh`, YouTrack REST, 기존 위키·GBrain 연결을 사용한다. pstack의 MCP·서비스별 어댑터 목록을 그대로 늘리지 않는다. 조사 산출물은 주제에 따라 위키/서비스 repo의 기존 위치에 남긴다.

### 사용 예부터 설계하고 대안은 비싼 결정에만 비교

`architect`의 호출자 사용 예 → 타입·시그니처 → 모듈 경계 순서는 기존 `codebase-design`·`domain-modeling`·`grill`에 넣을 만한 산출물 기준이다. `arena`는 같은 과제의 여러 해법을 비교하고, `swarm`은 다른 범위의 누락 없는 처리를 돕는다. 두 목적을 구분하는 것은 유용하다. [설계 가이드](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/docs/guide/04-design.md).

모든 함수 경계 변경에 복수 모델·프로토타입을 강제하지 않는다. 저장 형식, 공개 API, 동시성 소유권처럼 되돌리기 어려운 선택에서만 비용을 들인다. 모델·effort는 팀 라우팅을 따른다. `architect`의 기본 구현 진입은 설계 검토 요청에 적용하지 않는다.

### 성능 개선의 실험 조건 고정

`hillclimb`에서 가져올 것은 대표 workload, 민감도가 확인된 측정기, 고정 baseline, 반복 측정, 한 번에 한 가설, 회귀 검사, 채택·기각 기록이다. [원본](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/hillclimb.md).

기존 성능 진단 엔진에서 선택 사용한다. 특정 반복 횟수·모델·매 시도 커밋을 강제하지 않는다. 지표를 줄이기 위해 workload·판정 기준을 바꾸거나 correctness를 희생하지 않는다. 완료 기준은 같은 조건의 전후 측정과 회귀 통과다.

### Benny는 접수 자동화가 필요할 때만

Benny는 일반 slash skill이 아닌 휴면 자동화 팩이다. 분류와 재현·수정을 나누고, 출처 스레드·신뢰할 수 있는 판정 주체를 고정한다. 사람이 수정 중이면 멈추며, 기존 PR/commit이 있으면 경쟁 수정 대신 검증으로 전환한다. [의도 문서](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/automations/benny/FOR_AGENTS.md), [기존 수정 검증](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/automations/benny/skills/reproduce-and-fix-issues/references/verify-existing-fix.md).

향후 접수 자동화에는 중복 검사, 소유권 확인, 재현과 환경 막힘의 구분, 작성자와 검증자 분리를 차용한다. 첫 단계는 읽기 전용 분류·초안·증거 수집이면 충분하다. Slack 회신·YouTrack 생성/수정·PR 생성까지 자동화하려면 해당 쓰기에 대한 명시적 권한과 어댑터가 선행돼야 한다. 팀의 사업부 문체와 티켓 규격도 유지한다.

## 그대로 도입하지 않을 부분

| 항목 | 원본의 특성 | 팀 판단 |
|---|---|---|
| `poteto-mode` 상시 라우터 | 대화에서 유지되는 모드, playbook 단계 원문을 todo에 복사 | description 라우팅·상황당 동사 하나와 중복. 참고 자료만 흡수 |
| 원칙 스킬 23개 상주 | 원칙 인덱스와 개별 스킬을 함께 관리 | 기존 북극성·엔진과 중복. 컨텍스트 비용 대비 이득 낮음 |
| 고정 병렬 규모 | multi-phase plan의 live lane 10개, 특정 모델, unit/live/perf 일괄 요구 | 위험·변경 범위에 비례해 조정. 문서 수정에 런타임·성능 검사를 강제하지 않음 |
| 자동 PR·커밋·머지 기본값 | playbook마다 쓰기 범위와 시작 시점이 다름 | 이미 허가된 범위만 실행. 검토 요청을 실행 권한으로 확대하지 않음 |
| `no-comments`의 강한 삭제 기준 | 인정한 제약도 타입·테스트 등으로 옮기고 주석 제거 | 외부 시스템 함정·운영 이유·ADR 링크는 보존. 자동 일괄 삭제 불필요 |
| 호환 API 일괄 제거 | 호출자를 같은 wave에서 전환하고 구 API 삭제 | 내부 폐쇄 범위에서만. 레거시·외부 소비자·배포 순서·롤백 계약 우선 |
| Cursor 전용 실행 환경 | cloud agent, `/loop`, built-in skill, `.cursor/rules` | Claude/Codex 공통 계약으로 번안. 명령명만 바꿔 이식하지 않음 |
| 개인 스타일·bot UI 자동화 | 대화에서 개인 mode 생성, Grok bot webhook UI | 팀 공통 하네스 수요와 분리. 현재 도입 근거 부족 |

원본 자체가 모든 외부 쓰기를 무조건 허용하는 것은 아니다. `poteto-mode`는 되돌리기 어려운 작업의 정지를 명시하고, Benny는 draft PR까지만 허용한다. 문제는 각 흐름의 승인 범위·Git 컨벤션·도구가 팀과 다르다는 점이다. [모드](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/SKILL.md), [다단계 계획](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md), [레거시 경계 정책](../policies/engineering-policy.md).

## 적용 순서 제안

1. **서비스 하나에서 실행 검증 계약을 입증한다.** 기존 E2E/CLI/API 도구를 재사용하고 대표 기능 하나로 시작한다. 하네스에는 템플릿·포인터만 남긴다.
2. **하네스 행동 평가를 만든다.** 대표 오류 시나리오로 현재 기준선을 확보하고, 트리거 또는 증거 규격 변경 하나를 비교한다.
3. **리뷰 증거 규격을 작은 범위로 강화한다.** 안전 가정의 실행 입증을 고위험 변경에만 적용하고 기존 리뷰의 중복 문구를 줄인다.
4. **효과를 보고 확장한다.** 재현 성공률, 낡은 검증 문서 탐지, 미입증 완료 보고, 반복 읽기·재작업 비용으로 판단한다. 별도 스킬 신설은 재사용 수요가 확인된 뒤 결정한다.

현재 결과물은 이 검토 문서다. 기존 정책·스킬·카탈로그 변경, pstack 설치, 외부 게시·티켓 생성·커밋은 수행하지 않았다.

## 전체 스킬 적용 판정

판정의 의미: **보완**은 기존 엔진·계약에 일부 흡수, **기존**은 같은 목적의 수단이 있어 별도 설치 불필요, **선택**은 특정 작업에서만 사용, **보류**는 현재 수요·환경에 맞지 않음이다. 이름의 링크는 모두 검토 커밋의 원문을 가리킨다.

### 작업 스킬 24개

| 스킬 | 핵심 메커니즘 | 팀 적용 판정 |
|---|---|---|
| [architect](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/architect/SKILL.md) | 호출자 사용 예·타입·경계를 먼저 정하고 대안 설계 비교 | 선택: 기존 설계 엔진에 산출물 기준 흡수 |
| [arena](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/arena/SKILL.md) | 같은 과제를 독립 수행한 뒤 기준안과 장점 합성 | 선택: 되돌리기 비싼 결정에 한정 |
| [automate-me](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/automate-me/SKILL.md) | 최근 대화에서 개인 선호를 추출해 개인 mode 생성 | 보류: 개인 설정과 팀 정책 분리 |
| [blast-radius](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/blast-radius/SKILL.md) | 안전성의 핵심 가정을 찾아 실제 코드로 입증 | 보완: 기존 리뷰의 증거 규격 |
| [bro](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/bro/SKILL.md) | 직전 응답을 쉬운 말로 다시 설명 | 기존: `eli5`, `wait-what` 계열 |
| [create-verification-skill](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/create-verification-skill/SKILL.md) | 저장소 조사→실행 검증 계약·기능 지도→계약 자체 실증 | 보완: 최우선 서비스 시범 적용 |
| [figure-it-out](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/figure-it-out/SKILL.md) | 기존 playbook이 안 맞는 과제의 판정 가능한 실행 방식 설계 | 기존/선택: `grill`·`plan`·milestone 계약 활용 |
| [how](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/how/SKILL.md) | 코드의 실제 흐름·타입·핵심 경로 설명 | 기존: 분석·설명·온보딩 엔진 |
| [interrogate](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/interrogate/SKILL.md) | 독립 리뷰 결과를 채택·검토·기록·기각으로 합성 | 기존: 팀 교차 리뷰가 주 흐름. 기각 근거만 보완 후보 |
| [maintain-verification-skill](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/maintain-verification-skill/SKILL.md) | 기능별 소스·실행 대조, 지도 오류와 제품 오류 분리 | 보완: 생성 계약과 함께 도입 |
| [make-bot-ui](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/make-bot-ui/SKILL.md) | webhook으로 bot을 깨우는 UI와 접속 경로 구성 | 보류: Grok Bot·Tailscale 중심 별도 수요 |
| [no-comments](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/no-comments/SKILL.md) | 독립 주석 리뷰 후 제약을 구조로 옮기고 삭제 | 선택: 설명성 잡음 제거만. 의도·외부 계약 자동 삭제 금지 |
| [poteto-mode](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/SKILL.md) | 상시 모드, 원칙 인덱스, 상황별 playbook 라우팅 | 보류: 기존 `/ad:*` 라우팅과 중복 |
| [recall](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/recall/SKILL.md) | 자신의 최근 대화와 공유 기록에서 현재 맥락 재구성 | 기존/보완: context restore·위키·GBrain, 출처와 시점 보존 |
| [reflect](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/reflect/SKILL.md) | 세 관점의 회고→채택·기각·백로그→구조적 강제 검토 | 보완: 하네스 감사와 행동 평가 연결 |
| [setup-pstack](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/setup-pstack/SKILL.md) | 모델 역할·예산을 사용자 설정에 기록 | 기존: 팀 모델 라우팅·셋업을 SoT로 유지 |
| [show-me-your-work](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/show-me-your-work/SKILL.md) | 결정·이유·증거·결과 기록과 사후 감사 | 보완: 장시간 계획의 중요 판단 기록 |
| [swarm](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/swarm/SKILL.md) | 서로 다른 범위 또는 선언한 경쟁 분기를 병렬 처리 | 기존/선택: 범위·소유권·누락 보고 계약만 활용 |
| [tdd](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/tdd/SKILL.md) | 저렴한 재현 테스트의 red→green, 비싼 경우 실행 대안 | 기존: 설치된 `tdd`와 구현 seam 활용 |
| [teach](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/teach/SKILL.md) | 현재 동작과 배경을 엮어 단계적 그림으로 설명 | 기존: `teach`·`eli5`·온보딩 계열 |
| [technical-writing](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/technical-writing/SKILL.md) | 문서 목적과 독자에 맞춘 계층적 작성 기준 | 기존: 문서 정책과 생성 엔진. 필요한 예제만 흡수 |
| [typescript-best-practices](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/typescript-best-practices/SKILL.md) | 외부 입력·불법 상태·variant 처리를 타입으로 표현 | 선택: TS 서비스의 기존 lint·schema·타입 규칙 우선 |
| [unslop](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/unslop/SKILL.md) | 문장에서 상투적 표현과 불필요한 수사 제거 | 기존: 한국어 문체·PR·사업부 소통 정책 |
| [why](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/why/SKILL.md) | 기록의 근거 수준과 빈칸을 구분해 설계 배경 조사 | 보완: 사실·추론·미확인 규격 |

### 원칙 스킬 23개

아래 식별자는 모두 `principle-` 접두를 가진 독립 스킬이다. 대부분 원칙을 새로 설치할 필요 없이 기존 하네스·엔지니어링 규율로 설명할 수 있다.

| 원칙 | 핵심 | 팀 적용 판정 |
|---|---|---|
| [laziness-protocol](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-laziness-protocol/SKILL.md) | 문제를 해결하는 가장 작은 변경과 삭제 우선 | 기존: 작은 변경·불필요한 추상화 억제 |
| [foundational-thinking](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-foundational-thinking/SKILL.md) | 로직보다 데이터 구조와 공유 상태부터 결정 | 기존/보완: 도메인 모델링의 설계 산출물 |
| [redesign-from-first-principles](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-redesign-from-first-principles/SKILL.md) | 새 요구를 처음부터 존재한 조건처럼 설계 | 선택: 목표 설계 사고법. 대규모 재작성 지시로 사용 금지 |
| [attack-the-premise](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-attack-the-premise/SKILL.md) | 같은 전제의 수정이 반복 실패하면 전제를 재검토 | 보완: 디버깅 반복 실패 시 분기 기준 |
| [subtract-before-you-add](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-subtract-before-you-add/SKILL.md) | 죽은 구성·중복 검증·stub부터 제거 | 기존: 하네스 감사·스택 가지치기 |
| [minimize-reader-load](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-minimize-reader-load/SKILL.md) | 독자가 기억할 상태와 추적할 계층 축소 | 기존: deep module·문서 문체 규칙 |
| [outcome-oriented-execution](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-outcome-oriented-execution/SKILL.md) | 중간 호환 장치보다 목표 구조에 수렴 | 선택: 계획된 내부 전환. 운영 중간 상태·롤백은 보존 |
| [experience-first](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-experience-first/SKILL.md) | 구현 편의보다 사용자가 겪는 결과 우선 | 기존: acceptance·UX 검증으로 구체화 |
| [exhaust-the-design-space](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-exhaust-the-design-space/SKILL.md) | 대안 프로토타입을 비교한 뒤 결정 | 선택: 비싼 결정에만, 개수 강제 불필요 |
| [build-the-lever](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-build-the-lever/SKILL.md) | 반복 작업·증명을 재실행 가능한 도구로 남김 | 보완: 검증 생성기·행동 evaluator에 적용 |
| [model-the-domain](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-model-the-domain/SKILL.md) | 흩어진 조건을 도메인 구조로 표현 | 기존: `domain-modeling`·엔지니어링 표준 |
| [boundary-discipline](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-boundary-discipline/SKILL.md) | 외부 경계에서 검증하고 내부 타입을 신뢰 | 기존: Clean/Hexagonal·legacy adapter 규칙 |
| [type-system-discipline](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-type-system-discipline/SKILL.md) | 불법 상태 제거, 외부 파싱, variant 누락 방지 | 기존/선택: 언어별 규칙과 검사로 반영 |
| [make-operations-idempotent](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-make-operations-idempotent/SKILL.md) | 재시도·부분 실행 후에도 같은 상태로 수렴 | 기존/보완: DB migration 원칙을 하네스 쓰기 도구에도 적용 |
| [migrate-callers-then-delete-legacy-apis](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md) | 호출자 전환과 구 API 제거를 같은 wave에서 완료 | 선택: 모든 소비자를 소유한 내부 범위만 |
| [separate-before-serializing-shared-state](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md) | 잠금보다 공유 제거·작업 공간 격리 우선 | 기존/보완: 파일 소유권에 포트·프로필·데이터 격리 추가 |
| [prove-it-works](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-prove-it-works/SKILL.md) | 실제 산출물·동작을 관찰해야 완료 | 보완: 실행 검증 계약으로 구체화 |
| [fix-root-causes](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-fix-root-causes/SKILL.md) | 재현하고 원인을 확인한 뒤 수정 | 기존: `diagnosing-bugs`·`investigate` |
| [sequence-verifiable-units](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-sequence-verifiable-units/SKILL.md) | 각 단위를 검증 가능한 상태로 끝낸 뒤 진행 | 기존: milestone·TDD, 개발/검증/배포 Task 경계 유지 |
| [test-behavior-not-implementation](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-test-behavior-not-implementation/SKILL.md) | 공개 동작과 독립적인 기대값 검사 | 기존: 행동 테스트. 무의미한 구현 복제 테스트 억제 |
| [guard-the-context-window](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-guard-the-context-window/SKILL.md) | 큰 읽기를 위임하고 메인에는 판단 근거 유지 | 기존: smart zone·넓은 조사 위임 |
| [never-block-on-the-human](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-never-block-on-the-human/SKILL.md) | 가역적 작업은 진행하고 검토 가능한 결과 제시 | 기존: 조회 우선·사용자 승인 범위 존중 |
| [encode-lessons-in-structure](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/principle-encode-lessons-in-structure/SKILL.md) | 반복된 지시를 lint·metadata·검사로 바꿈 | 보완: 북극성의 기존 방향을 실증 도구로 완성 |

### Benny 자동화 스킬 3개

| 스킬 | 핵심 메커니즘 | 팀 적용 판정 |
|---|---|---|
| [setup-benny](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/automations/benny/skills/setup-benny/SKILL.md) | 팩과 사용자 설정 분리, 프로젝트 의존성·스레드 안전성 확인 | 보류: 실제 자동화 수요가 생긴 후 설치 계약 참고 |
| [triage-issue-reports](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/automations/benny/skills/triage-issue-reports/SKILL.md) | 출처 고정, 원인 기반 분류, 중복 검사, 제한된 tracker 쓰기 | 선택: 읽기 전용 분류·초안부터. 쓰기 보상 동작까지 별도 권한 필요 |
| [reproduce-and-fix-issues](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/automations/benny/skills/reproduce-and-fix-issues/SKILL.md) | 신뢰된 판정→소유권 확인→재현→기존 수정 검증 또는 제한된 수정 | 선택: 기존 수정이 있으면 검증으로 전환하는 경계 채택 |

## Playbook 23개 적용 판정

스킬과 별개인 상황별 실행 문서도 전수 확인했다. 일반 구현 흐름은 기존 엔진을 유지하고, 다음의 증거·범위 계약만 차용한다.

| Playbook | 가져올 부분 또는 유지할 경계 |
|---|---|
| [investigation](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/investigation.md) | 읽기 전용 조사와 구현의 종료점 분리 |
| [bug-fix](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/bug-fix.md) | 같은 사용자 경로에서 수정 전후 재현. 기존 디버깅 흐름에 흡수 |
| [perf-issue](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/perf-issue.md) | trace가 뒷받침하는 원인과 같은 조건의 전후 측정 |
| [hillclimb](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/hillclimb.md) | 측정기 고정·한 번에 한 가설·회귀 gate. 반복 수·커밋 강제 제외 |
| [runtime-forensics](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/runtime-forensics.md) | 실행 중 프로세스의 관측 증거와 원인 귀속. 진단 요청에서 수정으로 확대하지 않음 |
| [trace-forensics](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/trace-forensics.md) | 대형 trace를 조회 가능한 데이터로 바꾸고 원인 가설의 한계 표시 |
| [feature](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/feature.md) | 데이터 구조·사용자 동작·검증 결과 연결. 기존 구현 스킬 유지 |
| [refactoring](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/refactoring.md) | 변경 전 동작을 characterization/equivalence 검사로 고정 |
| [prototype](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/prototype.md) | 설계 질문을 결정할 최소 산출물과 관찰. 기존 prototype 활용 |
| [visual-parity](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/visual-parity.md) | baseline·비교 환경 고정. diff 0은 정확한 시각 동등성이 요구된 과제에만 |
| [authoring-a-skill](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/authoring-a-skill.md) | 구조·참조·실행 검증. 팀 SoT와 Codex alias 패리티 우선 |
| [eval](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/eval.md) | 동일 과제·격리 환경·중립 판정·실제 행동 기록 |
| [babysit](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/babysit.md) | 상태 조회와 수정 루프 구분, merge-ready와 merge 분리, 현재 PR 상태 재확인 |
| [shipping](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/shipping.md) | 작성자와 검증자 분리, revision에 묶인 판정. 자동 landing 기본값 제외 |
| [autonomous-run](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/autonomous-run.md) | 판정 가능한 종료 조건, 한 번에 한 검증 단위, 작업 흔적 보존 |
| [orchestrate](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/orchestrate.md) | 큰 프로그램에서 목표·범위·소유권·검증·중단·보고 계약. 소규모에 적용하지 않음 |
| [autopilot-full](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/autopilot-full.md) | owner와 독립 verifier 분리만 참고. 현재 자동 머지 체계 도입 보류 |
| [autopilot-stack](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/autopilot-stack.md) | 의존하는 변경의 순서와 개별 증거. stack·cloud agent 전제 도입 보류 |
| [session-pickup](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/session-pickup.md) | 기존 증거로 완료/대기 분리, 현재 상태와 대조 후 재개 |
| [pause-safely](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/pause-safely.md) | 안전한 작업 경계와 재개 노트. 일시정지 요청만으로 WIP 커밋 권한 추정 금지 |
| [multi-phase-plan](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md) | 단계별 산출물·판정·의존관계. 고정 10 lane·모든 PR의 perf 검사 제외 |
| [worktree-cleanup](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/worktree-cleanup.md) | 실제 경로·미커밋 작업·활성 세션·보존 사유 대조. 이름만 보고 삭제 금지 |
| [opening-a-pr](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/playbooks/opening-a-pr.md) | 작은 변경·근거 있는 PR 설명. 팀 브랜치·제목·승인 규격 우선 |

## 도구로 강제하는 범위와 한계

문서를 검사로 바꾸는 방향은 유용하지만, **검사기가 무엇을 판정하는지**를 구분해야 한다. `check-plan.mjs`는 문서 섹션·필수 문구·lane·증거 경로 표기 등을 검사한다. 앱의 성공이나 증거의 진실성을 실행해 확인하는 도구는 아니다. 특정 모델명·10 lane·영문 문체까지 고정하는 검사 항목은 팀의 소수 하드 게이트 원칙과 맞지 않는다. [검사기 원본](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/scripts/check-plan.mjs).

팀이 만들 도구는 “검증했다는 문구가 있는가”에서 멈추지 않고, 가능한 범위에서 명령 종료 결과·관찰값·대상 revision·증거 파일 존재를 확인해야 한다. 실제 동작 여부와 설계 판단은 여전히 증거를 읽는 검증자의 책임이다.

| 보조 도구 | 유용한 구현 | 그대로 가져오면 빠지는 부분 |
|---|---|---|
| `check-plan.mjs` | 계획 구조·필수 항목의 결정적 검사 | 미완료 `[ ]`도 형식상 유효. 실행 결과·증거 실재 검사 아님 |
| `orch/` | 파일 원장, atomic write, PR·SHA별 판정 기록 | open gate는 기록이며 실행 차단 장치 아님. evidence 문자열의 실제 파일·현재 PR 검증 필요 |
| `watch-pr/` | 충돌·리뷰 thread·CI를 분리하고 상태·종료 코드 반환 | `gateReason()`은 `CHANGES_REQUESTED`를 막지만 `REVIEW_REQUIRED`를 별도 gate로 막지 않음. `READY`를 팀 승인으로 해석 불가 |
| `worktree-audit.sh` | 실제 worktree와 dirty·PR·최근 사용 흔적으로 후보 분류 | 삭제 자체는 수행하지 않음. fetch·Cursor transcript·OS 의존성과 분류 이후 사람 판단 존재 |
| `bootstrap.ts` | lockfile 기반 의존성 설치 상태 확인 | 상태 조회용 CLI 실행도 누락 의존성의 설치·파일 쓰기를 유발할 수 있음 |
| `show-me-your-work/scripts/log.sh` | TSV 셀 개행·탭·스프레드시트 수식 입력 정리 | 기록된 판단·증거가 사실인지는 별도 검토 필요 |

소스 근거: [orch 저장소](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/scripts/orch/store.ts), [watcher 정책](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/scripts/watch-pr/policy.ts), [worktree 감사](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/scripts/worktree-audit.sh), [bootstrap](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/poteto-mode/scripts/bootstrap.ts), [판단 로그 helper](https://github.com/cursor/plugins/blob/5bf2b1544db739998121a306340631963c2ff3de/pstack/skills/show-me-your-work/scripts/log.sh).

이번 검토는 원문·코드 구조를 읽은 결과다. pstack 도구의 실행 안정성, 모델별 품질 향상, 팀 작업의 비용 절감 효과는 측정하지 않았다. 우선순위의 효과는 시범 적용과 행동 평가로 확인할 가설이다.
