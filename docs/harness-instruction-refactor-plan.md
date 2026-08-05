# 하네스 지시문 리팩토링 계획 — 제약 메타 계층 도입

> 상태: 제안 (2026-08-06, 감사 근거 확보). 실행은 Phase별 PR + 사용자 승인.
> 입력: ① 제약 메타 계층 제안 (규칙을 intent/invariant/heuristic으로 분리), ② mattpocock/skills 설계 패턴 검토.
> 근거 감사: 2026-08-06 전수 스캔 — policies 24 + 스킬 18 + docs/sprint 12 + templates 32.

## 1. 진단 — 감사 결과 요약

전체 지시문 약 1,435개 분류 결과:

| 클래스 | 비중 | 의미 |
|---|---:|---|
| INVARIANT (보안·정합성·사용자 확인 게이트) | ~11% | 진짜 "반드시" |
| POLICY (조직·팀 공식 정책) | ~44% | 명확한 예외 없으면 준수 |
| HEURISTIC (절차·도구·순서 권장) | ~41% | 더 나은 방법 있으면 변경 가능 |
| EXAMPLE (참고 패턴) | ~4% | 자유 대체 |

**핵심 문제 확인**: "반드시/필수/절대"가 실제 INVARIANT인 비율은 11%. 나머지 89%가 같은 강도로 표기되어 모델이 안전장치와 절차 권장을 구분할 수 없다. 의도(왜) 미기재율: templates ~65% > 스킬 ~48% > policies ~42% > docs/sprint ~33%.

**이미 있는 것** — 메타 계층은 신개념이 아니라 산발적 기존 관행의 표준화다:

- `policies/hypothesis-verification-order.md` — 순서 + 이유 + 위반 신호 + 예외 항목. 의도 미기재 0%. **표준 모델**.
- `docs/sprint/ticket-guide.md` — "분리하는 이유" 전용 절, "점진적 강화" 유연성 선언, 규칙별 확정 일자.
- `policies/internal-domain-policy.md` — "확정" vs "건별 협의" 구조적 이분화, 금지 표에 이유 컬럼.
- `policies/local-credentials-policy.md` — 규칙 뒤 "근거:" 절.
- `ad:work-prep` — 확인 게이트 3단 티어 (기본 진행 / 확인 필수 / 항상 금지).
- `ad:sprint-close-check` — "휴리스틱일 뿐, 최종 판단은 사용자" 자기 선언.
- mattpocock 패턴 기흡수 (2026-07-16): disable-model-invocation, 질문 규율, 리뷰 2축, 삭제 테스트, 얇은 alias. 직접 설치는 3중 중복으로 기각 — 판정 유지.

**대표 과잉제약 사례** (전체 15선 중 상위, 전수는 감사 기록 참조):

| 위치 | 현재 | 문제 |
|---|---|---|
| `ad:work-prep` 탐색 절차 | "진입점 후보 5개 이하로 추림" | 상한 근거 없음. 의도는 "핵심만 압축" |
| `ad:sprint-close-check` 5W1H 판정 | 키워드 6개 중 3개 미만 + 100자 컷 | 임의 수치 알고리즘. 모델이 직접 판단 가능. 자기 문서가 "오탐 난다" 인정 |
| `ad:harness-optimize` | Step 1→4 고정 + grep 파이프라인 4종 하드코딩 | 목표(경계 위반 탐지)가 아닌 수단(정규식)을 고정 |
| `ad:capacity-plan` | "시나리오 3개 필수 출력" | 고정 출력 개수 강제 |
| Step-N 고정 시퀀스 | sprint-workflow, velocity-guide, harness-optimize 등 관습화 | 순서가 목적인지 기본값인지 불명 |
| `ad:code-review` gh api 인코딩, `ad:weekly-report` login 비교 | 실패 사례 기반 "반드시" | 규칙 자체는 정당 — 출처 표기가 없어 잔재와 구분 불가 |

**중복·충돌** (13건 중 대표):

- DB/SP 승인+롤백 — **9개 파일** 재진술, 파일마다 첨부 목록 편차.
- 시크릿 취급 3원칙 — aws-secrets / datadog-api / local-credentials 각자 반복.
- 표준 Feature 체인 표 — 3곳 복제, "왜"는 SoT에만 생존.
- **충돌**: `engineering-policy.md` "2일 초과 분할" vs `ticket-guide.md` "Feature 1주/Task 1일" — 구버전 잔재.
- **드리프트**: `gstack-override-policy.md`에 "Claude Opus 4.6" 모델명 하드코딩.

## 2. 제안 판정 — 채택 / 변형 / 기각

### 채택

| # | 항목 | 형태 |
|---|---|---|
| A1 | **지시 강도 4등급** (invariant/policy/heuristic/example) | 표기 컨벤션으로. 규칙별 YAML 아님. invariant·policy는 현행 유지, heuristic은 "기본:" 접두 + 조정 조건 한 줄 |
| A2 | **판단 경계 + 우선순위 사다리** | 신규 정책 1개 (~40줄): 사용자 명시 요구 > 보안·정합성 > 승인 게이트 > 서비스 정책 > 팀 정책 > 스킬 지침 > 일반 관행. 불변 목록 / 조정 허용 조건 / 이탈 시 기록 규칙 포함. CLAUDE.md엔 링크 1줄 |
| A3 | **"근거:" 관례 표준화** | 실패 사례 기반 하드 게이트에 출처 한 줄 (일자·사건). 안전장치 vs 잔재 구분 가능하게. full lifecycle YAML(owner/review_after) 아님 |
| A4 | **harness-optimize `제약` 모드** | 기존 스킬 확장. 분류→문제→의도→권장조치(유지/완화/제거/도구화)→검증. Detect→Propose→삭제 테스트→PR. 강도 하향은 전부 review-required |
| A5 | **부정 → 긍정 표현 원칙** (원문 `writing-for-agents`) | 금지 서술은 금지 행동을 오히려 활성화("코끼리를 생각하지 마"). 목표 행동을 긍정문으로 서술, 금지는 긍정 대상과 짝지을 때만. skill-authoring-principles에 추가 |
| A6 | **환경 = SoT, 문서는 캐시** (원문 `writing-for-agents`) | `--help`·설정 파일·디렉토리 구조로 조회 가능한 사실을 문서에 재기술하면 캐시 — 조회 비용이 비쌀 때만 캐싱. harness-optimize grep 하드코딩·API 표 재기술류 판정 기준으로 사용 |

### 변형 채택

| # | 항목 | 변형 이유 |
|---|---|---|
| B1 | 평가 시나리오 (doc1 §5) | full regression suite 대신 대표 시나리오 5개 + 기존 삭제 테스트. 5인 팀엔 그게 상한 |
| B2 | 운영 리뷰 축 (doc2 §7 4축) | ad:code-review 2축 유지 + 레거시 배치·정산·외부연동 diff일 때만 운영 축(멱등성·재실행·부분실패 복구) 조건부 추가 |
| B3 | ADR 3조건 (doc2 §6) | engineering-policy 한 문단: 되돌리기 어려움 + 미래 의문 + 실제 트레이드오프 존재 — 셋 다 충족 시만 |
| B4 | 파일명 → 의미 기반 발견 (doc2 §4) | ai-usage-policy "필수 참조 5파일"을 "경계·의존·운영 절차를 발견 가능한 방식으로 확인, 표준 위치는 AGENTS.md 등" 으로 재표현 |
| B5 | hard/soft 의존 분류 (원문 ADR-0001) | 참조 없으면 **출력이 틀리는** 스킬만 명시적 참조 지시("X를 따른다, 없으면 Y 실행"), 출력이 **덜 날카로워질 뿐**인 참조는 완만한 서술로 강등. ad:* 스킬의 정책 링크 전수에 적용 |
| B6 | 기각 결정 기록 (원문 `.out-of-scope/` 패턴) | 기각 판정에 이유 + 탈출구 + 유발 사건을 남겨 재논의 방지. 신규 디렉토리 없이 `docs/skill-audit-baseline.md` 판정 절 형식 보강으로 수용 |

### 기각

| 항목 | 근거 |
|---|---|
| 디렉토리 재구성 (constitution/context/heuristics/…) | 기존 구조가 이미 기능적 등가 (policies≈constitution, catalog+서비스하네스≈context, commands≈skills, harness-optimize≈governance). 이동 비용 = Codex alias 18개 + KB 매핑 + 내부 링크 전부 파손. 이득 ~0 |
| 규칙별 YAML 카탈로그 (instruction-catalog.yaml) | 유지·토큰 비용, claude-md 최소화 원칙 충돌. `docs/skill-audit-baseline.md`가 이미 카탈로그 역할 |
| 매 실행 지시 감사 단계 | 제안 문서 스스로 비용 인정. A2 상시 선언 1곳으로 대체 |
| 스킬 세분화 (analyze-domain/trace-call-flow…) | 코딩 프로세스는 superpowers/gstack이 커버, ad:*는 업무 자동화. 세분화 = 3중 중복 재생산 (2026-07-16 기각 판정 유지) |
| mattpocock 스킬 직접 설치 | 동일 — 기각 판정 유지 |

## 3. 실행 계획

### Phase 1 — 기반 (PR 1개, 저위험)

1. `policies/instruction-precedence-policy.md` 신설 (A1+A2+A3 통합, ~40줄).
2. CLAUDE.md 핵심 규칙에 링크 1줄.
3. `policies/skill-authoring-principles.md` 체크리스트에 5단계 "강도 표기" 추가.

### Phase 2 — 제약 감사 루프 (PR 2~n, 항목별 사용자 승인)

1. `ad:harness-optimize`에 `제약` 모드 추가 (A4).
2. 1차 재표현 — 15선 우선순위 상위:
   - work-prep "5개 이하" → "핵심 진입점만, 선정 근거 제시"
   - sprint-close-check 키워드 카운트 → 모델 판단 + 후보 사유 제시 (알고리즘 명세 강등)
   - harness-optimize grep 4종 → 목표 서술 + 예시 명령 표기
   - Step-N 시퀀스 → 완료 기준 중심, 순서는 기본값 명시
   - gh api·login 비교 규칙 → **유지** + "근거:" 부착
3. 중복·충돌 정리: DB/SP 승인 9곳 → SoT 1곳+링크 / 시크릿 3원칙 공통화 / engineering-policy "2일" 갱신 / "Opus 4.6" 모델명 제거.

### Phase 3 — 선택 확장

B2(운영 축), B3(ADR 기준), B4(의미 기반 발견), templates 이유 재인용.

## 4. mattpocock/skills 원문 전수 확인 (2026-08-06)

레포 클론 후 활성 스킬 25개(총 1,590줄, 평균 ~64줄) + 메타 문서(CLAUDE.md, CONTEXT.md, `.agents/`, `.out-of-scope/`) 전부 확인. 분석 문서 ②의 인용은 정확했고, 문서가 다루지 않은 추가 발견을 아래에 반영.

### 구조 차원

| 원문 패턴 | 판정 | 적용 |
|---|---|---|
| 버킷 생명주기 (promoted/misc/in-progress/deprecated) | 개념만 | 디렉토리 버킷은 슬래시 네임스페이스 파손 — `docs/skill-audit-baseline.md` 판정(활성/관찰/유지/삭제)이 이미 동일 기능. 구조 이동 불요 |
| `.out-of-scope/` — 기각 요청 KB, triage 접수 시 대조 | 채택 (B6) | 기각 기록에 이유+탈출구+유발 사건. harness-optimize가 재제안 전 대조 |
| `ask-matt` 라우터 — 스킬 간 flow 지도 + "거짓말하는 라우터" 유지보수 규칙 | 변형 채택 | ad:* flow 지도(ticket→work-prep→code-review→weekly-report, 월말 on-ramp 등)를 harness-guide 한 절로. 스킬 증감 시 라우팅·지도 동기 갱신을 harness-optimize 체크리스트에 |
| 스킬별 독립 docs 페이지 + "It's working if" | 기각/축소 | 내부 팀엔 이중 문서 과잉. "작동 신호" 한 줄만 audit baseline 열로 흡수 검토 |

### 컨셉 차원

| 원문 | 판정 | 비고 |
|---|---|---|
| `writing-for-agents` — 부정→긍정, 환경=캐시, 정보 계층 사다리, 완료 기준의 demand 레버 | A5·A6 채택 + 가지치기 4종화 | 팀 가지치기 3종(중복·퇴적물·무동작)에 **캐시(환경 재기술)** 추가. 사다리·완료기준은 기흡수분의 정밀화 |
| "사실은 에이전트 몫, 결정은 사용자 몫" (grilling) | 기흡수 확인 | 팀 질문 규율의 원전 |
| **frontier 라운드 질문** (독립 질문은 한 라운드에 번호+추천안 일괄) | 긴장 존재 — 사용자 판단 필요 | 팀 규율은 "한 번에 하나씩" (2026-07 의도적 채택). 원문은 독립 결정 다수일 때 라운드 일괄이 왕복을 줄인다는 입장. ad:ticket 인터뷰에 선택 적용 여부는 팀 결정 사항 |
| tracer-bullet 수직 슬라이스 + blocking edges (to-tickets) | 부분 적용 | 팀 단계 분리(개발/검증/배포)는 조직 현실(QA 주체 분리) 기반 수평 분할 — 유지. 수직 슬라이스·의존 엣지는 **개발 Task 내부** 분할에 적용 (아래 스킬 매핑) |
| expand–contract 티켓 시퀀싱 | 참고 | DB 이관·CDC 티켓 분할 시 참조 (팀은 개념 기보유) |
| phase boundary 결정 트리 (continue/clear/handoff/subagent/compact) | 참고 | 세션 위생 가이드로 harness-guide 언급 후보. 저우선 |

### 스킬 레벨 매핑 (ad:* 직접 적용)

| 팀 스킬 | 원문 출처 | 적용 항목 |
|---|---|---|
| ad:ticket | to-tickets | ① Task 간 **blocking edges**를 YouTrack 의존 링크로 등록, frontier(선행 완료된 것부터) 순 착수 표기 ② 본문에 파일 경로·스니펫 금지("빨리 썩는다") — ai-usage-policy 기존 규칙을 티켓 본문 규칙으로 명문화 ③ Task acceptance criteria 체크박스 |
| ad:work-prep | triage | ① **redundancy check** — 접수 요청을 도메인 개념으로 기존 구현 검색, "어디를 찾아봤는지" 보고 ② 기각 기록 대조 ③ 버그 제보는 verify-claim(재현) 먼저 — hypothesis-verification-order와 정합, 명시 스텝화 |
| ad:code-review | code-review | ① smell 3원칙 명문화: 저장소 표준 > 일반 스멜 / 스멜은 항상 판단 콜(위반 아님) / 도구가 잡는 건 스킵 ② fixed-point 사전 검증(ref 해석+diff 비어있음)을 본 작업 전 fail-fast로 |
| ad:harness-optimize | writing-for-agents | 가지치기 대상 3종→**4종**: 중복·퇴적물·무동작 + **캐시**(환경이 SoT인 사실의 재기술 — grep 파이프라인·API 필드표류) |
| (신규 후보) 질의서 생성 | to-questionnaire | 사업부·개발3팀 등 타 조직에 결정을 물어야 할 때 "**보내는 것**을 인터뷰"(수신자·필요 답변)해 질문지 생성. business-stakeholder-communication-policy와 연결. 신규 스킬은 상주 비용 발생 — Phase 3에서 사용자 판단 |
| ad:explain/tldr | wait-what, teach | 기능 중복 — 도입 불요 |

## 5. 검증

- **대표 시나리오 5**: 티켓 생성 / 주간보고 / 코드리뷰(레거시 diff) / work-prep(콜그래프 無 서비스) / sprint-close-check. 재표현 전후 각 1회 실행 비교 — 삭제 테스트의 확장.
- 강도 하향(반드시→기본) 변경은 예외 없이 review-required. INVARIANT·POLICY 등급 변경은 이 계획 범위 밖 (별도 팀 합의).
- 판정 지표: 필수 게이트 위반 0 / 산출물 필수 항목 누락 0 / 불필요 절차·도구 호출 감소.
