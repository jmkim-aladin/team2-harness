# 가용 용량 분석 (capacity plan)

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

다음 달 개인 가용 맨데이 + 팀 dev 수용량 SP를 산출하고, `{YYMM}-planned` 태그 티켓 SP 합계와 비교하여 초과 여부를 판정합니다. 산식·양식 출처:
- `docs/sprint/velocity-guide.md` (velocity 정의)
- `docs/sprint/story-point-guide.md` (SP 환산)
- `docs/sprint/2026-04-capacity-analysis.md` (개인 가용 맨데이 양식)
- **YouTrack KB DEV2-A-1122** (Velocity-OKR 스프린트 정책 — BD PLAN 번다운 → 다음달 수용량 산식)

## 사용법

```
/ad:capacity-plan                              # 다음달, 본인(김정민)
/ad:capacity-plan 2026-06                      # 명시 월, 본인
/ad:capacity-plan 2026-06 조은흠                # 명시 월, 명시 인원
/ad:capacity-plan 2026-06 조은흠 저장           # + Obsidian vault 저장
/ad:capacity-plan 다음달                       # 다음달 키워드
/ad:capacity-plan 이번달                       # 이번달
```

인자 파싱:
- `YYYY-MM` → 대상 월
- `다음달`/`이번달` → 오늘 기준 산출
- 한글/영문 → 담당자 이름
- `저장`/`save` → Obsidian vault 저장 플래그
- 미지정: 대상 월 = 다음 달, 담당자 = 김정민

## 팀원 매핑 (dev role, 정직원만)

로스터 SoT: [policies/team-members.md](../../../policies/team-members.md) — 정규직 표에서 **개발자 역할만** 합산 (팀장·디자이너·기획자·프리랜서 제외).

- capacity 특화 예외: 강인용(iyk)은 2026-07 정규 전환 — 이전 스프린트 velocity baseline에 미포함

## 스프린트 구조 (팀장 지침)

- **스프린트 기간**: 매월 1일 ~ 26일 (4주 운영, 6/1~6/26 사례)
- **D-5 (마지막 주)**: 27일~말일+α 5근무일. 회고·다음 달 계획·이월 정리 전용. **스프린트 외**
- 월별 정확 D-5 범위는 팀장이 매월 공지 (예: 6월 D-5 = 6/29~7/3)

## 가용 맨데이 산식

```
스프린트 평일 (해당 월 1~26일 평일)
  - 공휴일
  - 본인 PTO/연차 (사용자 입력)
  = 가용 평일
  × 계획업무 비율 (기본 50% / 팀 지침 시 100%)
  = 최종 가용 맨데이
```

- 스프린트 평일: `1일~26일` 범위 평일만 카운트 (4주 ≈ 20일)
- D-5는 별도 운영이므로 차감하지 않음 (스프린트 외)
- 공휴일: 사용자에게 질문 (한국 공휴일 자동 판별 도구 없음). 스프린트 범위(1~26일) 내만 카운트
- PTO: 사용자에게 질문
- **계획업무 비율**:
  - 기본 50% (운영업무 50% 보정) — `docs/sprint/2026-04-capacity-analysis.md` 4월 패턴
  - **6월부터 팀장 지침으로 100%** — 매월 지침 확인 후 입력
  - 다른 비율도 사용자 입력 허용

## SP 환산

`docs/sprint/story-point-guide.md` 기준 (3 = M = 표준 ≈ 1일 앵커).

| SP | 사이즈 | 맨데이 |
|----|--------|--------|
| 1 (XS) | 매우 단순 | ~0.25일 |
| 2 (S) | 단순 | ~0.5일 |
| 3 (M) | 표준 | ~1일 |
| 5 (L) | 복잡 | ~2일 |
| 8 (XL) | 매우 복잡 | ~3.5일 |
| 13 | 분할 필요 | — (분할 권고) |

미산정 Task 기본 추정: **0.5일** (가이드 4월 분석 사례 기준). 협의/논의 성격은 SP 1 일괄 권고.

## 팀 수용량 산식 (KB DEV2-A-1122 BD PLAN 패턴)

```
다음달 수용량 = 전월 dev velocity × 80% × (다음달 영업일 / 전월 영업일)
```

- 80% = 계획 설계 안전 마진 (KB 패턴, 사용자 변경 가능)
- 가용률 보정 = 영업일 비율
- 전월 velocity = `{YYMM-1}-planned` 태그 dev role 전체 SP **합산** (단순 sum, 인당 평균 아님)

### Velocity 입력 범위 (사용자 질문)

KB는 `완료(Done) SP만` baseline 으로 사용. 단 사용자가 `진행 포함` 요구 시 (예: 월 중 스냅샷):
- **완료만**: 보수적 baseline (KB 표준)
- **완료 + 진행**: 현재 burn 추세
- **완료 + 진행 + Open**: planned 전체 (낙관 baseline)

기본 `완료만`. 다른 옵션은 사용자 입력으로 전환.

### AASM 가중치 (팀장 지침)

AASM 프로젝트 SP는 별도 가중치 적용 (기본 30%).

```
AASM 환산 = AASM SP × aasm_weight (기본 0.3)
환산 velocity = AASM 환산 + 비AASM SP
```

이유: AASM은 개인 도구·실험 성격으로 팀 baseline 산정에서 비중 축소. 매월 팀장 지침 확인.

### 시나리오 제시 (필수)

- 전체 (AASM 100%)
- AASM 제거 (0%)
- **AASM 가중치 적용 (기본 30%, 권장)**

3 시나리오 모두 출력하여 비교 가능하도록 한다.

## YouTrack 쿼리 (BD PLAN 스냅샷)

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"

# 전월 BD PLAN 스냅샷 (예: 5월 = 2605-planned, dev 전체)
# YouTrack 쿼리는 --data-urlencode 사용 필수 (공백 포함 query)
curl -s -G -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  --data-urlencode "query=tag: 2605-planned" \
  --data-urlencode "fields=idReadable,summary,customFields(name,value(name,presentation))" \
  --data-urlencode '$top=500' \
  "$BASE/api/issues"

# 개인 과거 완료 velocity (예: 2026-04 jmkim)
curl -s -G -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  --data-urlencode "query=project: DEV2 Assignee: jmkim resolved date: 2026-04-01 .. 2026-04-30" \
  --data-urlencode "fields=idReadable,customFields(name,value(name,presentation))" \
  --data-urlencode '$top=300' \
  "$BASE/api/issues"

# 대상 월 계획 SP (예: 6월 = 2606-planned, 본인)
curl -s -G -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  --data-urlencode "query=tag: 2606-planned Assignee: jmkim" \
  --data-urlencode "fields=idReadable,summary,customFields(name,value(name,presentation))" \
  --data-urlencode '$top=200' \
  "$BASE/api/issues"
```

**파싱 주의**:
- `Story points` field는 `value`가 **int/float 직접** (dict 아님). `isinstance(v,(int,float))` 분기 필요
- `tag` 검색은 정확 매칭 — `tag:` 다음 공백 필수 (`tag: 2606-planned`)
- 날짜 범위 syntax: `resolved date: 2026-04-01 .. 2026-04-30` (공백 포함, `--data-urlencode` 필수)
- AASM 식별: `summary` 에 `[AASM]` prefix 포함 여부로 판단

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | YouTrack API 인증 토큰 |
| `$YOUTRACK_BASE_URL` | YouTrack 베이스 URL (기본: `https://aladincommunication.youtrack.cloud`) |

## 실행 지침

1. **인자 파싱** → 대상 월·담당자·저장 여부
2. **가용 맨데이 입력 수집** (사용자 질문):
   - 스프린트 범위 확인 (기본 1~26일, 팀장 지침 시 변경)
   - 공휴일 수 (스프린트 범위 내)
   - 본인 PTO/연차 일수
   - 계획업무 비율 (기본 50%, 6월부터 팀장 지침 100%)
3. **가용 맨데이 계산** → 산식 표 출력
4. **전월 BD PLAN 스냅샷 조회** (`tag:{YYMM-1}-planned`, dev role 전체):
   - 담당자별 SP × 상태(완료/진행/Open/Won't fix) 집계
   - `[AASM]` prefix vs 비AASM 분리
5. **AASM 가중치 적용** → 환산 velocity 계산 (기본 0.3, 사용자 변경 시만 질문)
6. **6월 수용량 환산** (KB 산식) → 3 시나리오 (전체/제거/가중치) 모두 출력
7. **개인 과거 velocity 참고 조회** → 최근 3개월 완료 SP 추이 (보조 지표)
8. **대상 월 계획 SP 조회** → `{YYMM}-planned` 태그 본인 담당 Epic/Feature/Task 트리 (태그 미생성 시 skip)
9. **판정** → 필요 맨데이 vs 가용 맨데이 + 팀 수용량 vs 개인 환산 SP 정합 확인
10. **조정안 제안** (초과 시): OKR KR 우선순위 컷 / 균형 / 이월
11. **마크다운 출력**
12. **저장 인자 있으면** Obsidian vault 저장

## 출력 양식

```markdown
# {YYYY}년 {M}월 계획업무 용량 분석 ({담당자})

> 기준일: {오늘} | 출처: YouTrack DEV2 `{YYMM}-planned` 태그 + KB DEV2-A-1122 BD PLAN 패턴
>
> 팀장 지침: 스프린트 = {M}/1~{M}/26 (4주), D-5 = {D5_RANGE}, SP {R}% 활용

## 가용 맨데이

| 항목 | 수치 |
|------|------|
| 스프린트 평일 ({M}/1~{M}/26, 4주) | {N}일 |
| 공휴일 | -{H}일 |
| PTO/연차 | -{P}일 |
| D-5 별도 운영 ({D5_RANGE}) | 차감 없음 (스프린트 외) |
| 계획업무 비율 {R}% | {N2} × {R/100} = **{가용}일** |

## 전월 BD PLAN 번다운 스냅샷 (dev role)

| 담당자 | 전체 SP | 완료 | 진행 | Open | Won't fix | AASM SP | 비AASM |
|--------|---------|------|------|------|-----------|---------|--------|
| ... | ... | ... | ... | ... | ... | ... | ... |
| **개발 합** | **...** | **...** | **...** | **...** | **...** | **...** | **...** |

### AASM 가중치 환산 ({weight}% 적용)

```
AASM 환산 = {aasm_sp} × {weight} = {a}
비AASM   = {non_aasm_sp}
전월 dev 환산 velocity = {a} + {non_aasm_sp} = **{weighted_sp} SP**
```

### {대상월} 수용량 환산

**산식**: 전월 velocity × 80% × ({대상월}/{전월} 영업일)
- 전월 영업일: {prev_wd}일
- {대상월} 영업일: {cur_wd}일
- 보정 = {cur_wd}/{prev_wd} = **{ratio}**

| 시나리오 | 전월 velocity | ×80% | ×가용률({ratio}) | {대상월} 수용량 |
|----------|---------------|------|-----------------|------------------|
| 전체 (AASM 100%) | ... | ... | ... | **약 ... SP** |
| AASM 제거 (0%) | ... | ... | ... | **약 ... SP** |
| **AASM {weight}% 반영 (권장)** | **...** | **...** | **...** | **약 ... SP** |

## 개인 과거 Velocity 추이 (참고)

| 월 | 완료 티켓 | 산정 SP | 미산정 건수 |
|----|-----------|---------|-------------|
| {M-1} | ... | ... | ... |
| {M-2} | ... | ... | ... |
| {M-3} | ... | ... | ... |

## 본인 계획 SP ({YYMM}-planned)

(Epic/Feature 트리별 표 — 태그 미생성 시 skip)

## 판정

```
가용 맨데이:           {가용}일
팀 수용량 (AASM {weight}%): {수용량} SP
본인 환산 가용 SP:     {가용}일 × 3 SP/일 = {가용*3} SP
정합:                  팀 수용량 / 본인 환산 = {비율}
```

## 조정안 / 제안

(KR 우선 / 균형 / 이월 항목)
```

## 저장 (옵션)

- vault 경로: `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/`
- 파일 경로: `wiki/processes/capacity/{YYYY-MM}-{담당자}.md`
- 파일 존재 시 덮어쓰기 전 사용자 확인
- frontmatter:

```yaml
---
type: capacity-plan
target_month: 2026-06
person: 김정민
generated_at: 2026-05-26
sprint_window: "2026-06-01..2026-06-26"
d5_window: "2026-06-29..2026-07-03"
working_days_raw: 20
holidays: 1
pto: 0
plan_ratio: 1.0
available_md: 19
prev_bd_plan_snapshot:
  taken_at: 2026-05-26
  source: "tag:2605-planned, dev role"
  total_sp: 124
  done_sp: 96
  inprogress_sp: 1
  open_sp: 25
  wontfix_sp: 2
  aasm_sp: 80
  non_aasm_sp: 44
aasm_weight: 0.3
prev_velocity_weighted: 68
working_days_prev: 18
working_days_target: 19
availability_ratio: 1.056
planning_buffer: 0.8
target_capacity_scenarios:
  all_aasm_100: 105
  aasm_excluded: 37
  aasm_weighted: 57
recommended_baseline_sp: 57
planned_tag: 2606-planned
planned_tag_exists: false
status: draft
---
```

## 사용 예 (참조)

- `wiki/processes/capacity/2026-06-김정민.md` (Obsidian vault) — 5월→6월 환산 적용 사례. AASM 30% 시나리오로 6월 baseline 57 SP 산출.

## 주의

- 가용 맨데이·팀 수용량은 **목표가 아닌 입력값** (velocity-guide.md 철학)
- 초과 판정 = 즉시 컷 신호 아님. 우선순위 재배치 + OKR 연계 검토
- 미산정 Task 다수면 SP 산정 회의 먼저 권고
- 한국 공휴일 자동 판별 없음 → 사용자 입력 필수
- YouTrack 쿼리는 `--data-urlencode` 사용 필수 (공백 포함 query). `tag: {YYMM}-planned` 정확 매칭
- `Story points` customField value는 int/float 직접 (dict 아님) — 파싱 시 타입 분기 필요
- 박민석 등 SP 산정 누락 케이스 다수 — baseline 정확도 위해 산정 완료 권고
- AASM 가중치는 팀장 지침. 변경 시 frontmatter `aasm_weight` 갱신

ARGUMENTS: $ARGUMENTS
