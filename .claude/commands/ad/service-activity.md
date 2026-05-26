# 서비스 작업 활동 조회

YouTrack 티켓을 서비스 태그·기간으로 필터링하여 팀 작업 현황을 정리합니다. 운영 위키에 스냅샷 저장 가능.

## 사용법

```
/ad:service-activity max                            # 만권당, 지난주(월~일)
/ad:service-activity tobe                           # 투비, 지난주
/ad:service-activity max tobe                       # 다중 서비스, 지난주
/ad:service-activity max 이번주                      # max, 이번주(월~일)
/ad:service-activity tobe 7d                        # tobe, 최근 7일
/ad:service-activity max 2026-05-18..2026-05-24     # 명시 기간
/ad:service-activity max 저장                        # 결과 + Obsidian vault 저장
```

인자 파싱:
- 서비스 슬러그(`max`, `tobe`, `shopping`, `naru`, `bazaar`, `aasm`, `storefront`, `caravan`, `blog`) → `services`
- `이번주` / `지난주` / `Nd` / `YYYY-MM-DD..YYYY-MM-DD` → `period`
- `저장` 또는 `save` → Obsidian vault 저장 플래그
- 미지정: services 필수, period 기본 = `지난주`

## 서비스 → YouTrack 태그 매핑

티켓 `summary` 앞 대괄호 prefix 기준. 신규 서비스 추가 시 이 표에 행 추가.

| 슬러그 | summary 패턴 (OR 조건) |
|--------|------------------------|
| max | `[만권당]`, `[max]` |
| tobe | `[투비]`, `[tobe]` |
| shopping | `[알라딘쇼핑]`, `[쇼핑]`, `[shopping]` |
| naru | `[나루]`, `[naru]` |
| bazaar | `[바자]`, `[bazaar]` |
| aasm | `[aasm]` |
| storefront | `[스토어프론트]`, `[storefront]`, `[b2b-store]` |
| caravan | `[가상대기열]`, `[caravan]` |
| blog | `[블로그]`, `[북플]`, `[blog]` |

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | YouTrack API 인증 토큰 |
| `$YOUTRACK_BASE_URL` | YouTrack 베이스 URL (기본: `https://aladincommunication.youtrack.cloud`) |

## API 호출

YouTrack 쿼리 파서가 `()` 그룹 OR를 지원하지 않으므로 태그 패턴별 별도 호출 후 ID 기준 dedup.

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"

# 태그 패턴별 호출 (URL 인코딩 필수)
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$BASE/api/issues?query=project:DEV2+updated:{FROM}+..+{TO}+summary:{TAG_ENCODED}&fields=idReadable,summary,customFields(name,value(name,login)),updated,resolved&\$top=200"
```

`customFields`에서 추출: `State`, `Assignee`, (`Subsystem` 있으면 보조).

## 기간 계산

- `지난주`: 이번주 월요일 - 7일 ~ - 1일 (예: 오늘 2026-05-26 화 → `2026-05-18..2026-05-24`)
- `이번주`: 이번주 월요일 ~ 일요일
- `Nd`: 오늘 - N일 ~ 오늘
- `YYYY-MM-DD..YYYY-MM-DD`: 그대로 사용

bash 계산 예:
```bash
LAST_MON=$(date -v-mon -v-7d +%Y-%m-%d)  # macOS
LAST_SUN=$(date -v-mon -v-1d +%Y-%m-%d)
```

## 출력 양식

서비스별 그룹 → 상태별 그룹 → 담당자 묶음. 완료(Closed/Fixed/Verified), 진행(In Progress), 신규/예정(Open/Backlog)로 단순화.

```markdown
# {서비스명} 작업 — {기간} ({YYYY-MM-DD ~ YYYY-MM-DD})

## 완료
- DEV2-XXXX (담당자) 제목 원문

## 진행 중
- DEV2-XXXX (담당자) 제목 원문

## 신규/Backlog
- DEV2-XXXX (담당자) 제목 원문

## 요약
- 핵심 흐름 2-3줄 (마이그레이션/이벤트/장애 등 묶음 단위)
```

티켓 제목은 YouTrack 원문 유지 (대괄호 prefix 포함, YouTrack 자동 링크 보존).

## 실행 지침

1. 인자 파싱 → 서비스 목록·기간·저장 여부 결정
2. 서비스별 태그 패턴 전개 → YouTrack API 호출
3. ID 기준 dedup, 상태/담당자 추출
4. 양식에 맞춰 마크다운 생성
5. `저장` 인자 있으면 Obsidian vault에 저장 (아래)
6. 화면 출력

## 저장 (옵션)

- vault 경로: `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/`
- 파일 경로: `wiki/activity/{YYYY-MM-DD}-{services}-{from}_{to}.md`
  - 예: `wiki/activity/2026-05-26-max-tobe-2026-05-18_2026-05-24.md`
- 파일 존재 시 덮어쓰기 전 사용자 확인
- frontmatter:

```yaml
---
type: service-activity
services: [max, tobe]
period_from: 2026-05-18
period_to: 2026-05-24
generated_at: 2026-05-26
---
```

## 주의

- KB 자동 반영 금지 (Obsidian 로컬 저장만)
- 신규 서비스 추가 시 본 문서의 매핑 표 갱신
- summary 패턴은 prefix 기준이라 본문에 우연히 포함된 경우는 매칭되지 않음 (의도된 동작)
- YouTrack 쿼리 `()` 그룹 OR 미지원 → 태그별 별도 호출 + dedup

ARGUMENTS: $ARGUMENTS
