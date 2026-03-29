# OKR 조회 및 작성

팀/개인 OKR을 조회하거나, 2분기 개인 OKR 초안을 작성합니다.

## 사용법

```
/ad:okr                          # 현재 분기 팀 OKR 조회
/ad:okr 연간                     # 연간 팀 OKR 조회
/ad:okr 1분기                    # 1분기 팀+개인 OKR 조회
/ad:okr 2분기                    # 2분기 팀 OKR 조회
/ad:okr 김정민                   # 해당 팀원의 OKR 전체 조회
/ad:okr 김정민 2분기 작성         # 2분기 개인 OKR 초안 작성/수정
/ad:okr 동기화                   # YouTrack KB에서 최신 OKR 가져오기
```

## 하네스 OKR 문서 위치

| 파일 | 내용 | YouTrack KB |
|------|------|-------------|
| `docs/okr/2026-team-okr.md` | 팀 연간 OKR | REF-A-2175 |
| `docs/okr/2026-q1-team-okr.md` | 1분기 팀 + 개인별 OKR | REF-A-2470 |
| `docs/okr/2026-q2-team-okr.md` | 2분기 팀 OKR (담당자·월 배정) | REF-A-3122 |
| `docs/okr/2026-q1-kimjeongmin.md` | 김정민 1분기 개인 OKR | REF-A-2566 |
| `docs/okr/2026-q2-kimjeongmin.md` | 김정민 2분기 개인 OKR | - |
| `docs/okr/2026-q2-joeunheum.md` | 조은흠 2분기 개인 OKR | - |

## 팀원 이니셜 매핑

| 이니셜 | 이름 | 구분 | 파일명 접미사 |
|--------|------|------|--------------|
| KJM | 김정민 | 정규 | kimjeongmin |
| JEH | 조은흠 | 정규 | joeunheum |
| JJY | 조윤주 | 정규 | joyunju |
| AHR | 안혜련 | 정규 | anhyeryeon |
| LHM | 이현민 | 정규 | leehyunmin |
| KJS | 김정실 | 정규 | kimjeongsil |
| LYR | 이유림 | 정규 | leeyurim |
| JYJ | 조주영 | 프리랜서 | jojuyoung |
| IYK | 강인용 | 프리랜서 | kanginyong |
| PMS | 박희수 | 프리랜서 | parkheesu |

## 실행 지침

### 조회 모드

1. 사용자 요청에 맞는 `docs/okr/` 파일을 읽어서 표시
2. 팀원 이름으로 요청 시 해당 팀원의 모든 분기 OKR을 조회
3. 팀 OKR 조회 시 담당자 배정 현황도 함께 표시

### 작성 모드

개인 OKR 초안 작성 시 아래 원칙을 따릅니다:

1. **팀 OKR에서 담당 항목 추출**: `docs/okr/2026-q2-team-okr.md`에서 해당 팀원 이니셜이 배정된 KR 항목을 식별
2. **1분기 OKR 참조**: 해당 팀원의 1분기 OKR 스타일과 역할 맥락을 참조
3. **연간 OKR 정렬**: 연간 목표와의 연결고리 확인

#### OKR 작성 규칙

- **Objective**: 해당 분기에 담당자가 달성할 핵심 목표를 1문장으로 (팀 KR과 연계)
- **Key Results**: 각 KR은 반드시 수치화된 지표 포함
  - 완료율/달성율: `100%`, `80% 이상`
  - 건수/종수: `1건 이상`, `15개+`, `5종`
  - 기간: `2주 이내`, `4주차까지`
  - 장애/오류: `0건 유지`
  - 커버리지: `50% 이상`, `80% 이상`
- **월별 포커스**: 각 KR이 어느 월에 집중되는지 명시
- **팀 KR 연계**: 각 KR이 팀 OKR의 어떤 KR에 기여하는지 명시
- **협업 포인트**: 다른 팀원과 동시 진행되는 항목이 있으면 동기화 포인트 표시

#### 출력 형식

```markdown
# {이름} 2026 {N}분기 개인 OKR (초안)

> 상위: REF-A-3122 (2분기 팀 OKR) | REF-A-2175 (연간 팀 OKR)

## Objective
{1문장 핵심 목표}

## Key Results

### KR1. {제목} ({월})
> 팀 KR{N} 연계 — {팀 KR 내용 요약}
- {수치화된 지표 1}
- {수치화된 지표 2}
...

## 월별 포커스
| 월 | 주요 목표 | 팀 KR | 핵심 지표 |
...
```

### YouTrack 동기화 모드

1. YouTrack KB API로 최신 OKR 문서 조회
2. 하네스의 기존 문서와 비교
3. 변경 사항이 있으면 업데이트

```bash
BASE="https://aladincommunication.youtrack.cloud"
# 팀 연간 OKR
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-2175?fields=id,idReadable,summary,content,updated"
# 1분기
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-2470?fields=id,idReadable,summary,content,updated"
# 2분기
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-3122?fields=id,idReadable,summary,content,updated"
```

## 스프린트 연계

OKR 작성 시 스프린트 운영 문서도 참조합니다:
- `docs/sprint/sprint-planning-overview.md` — 맨데이 배분 및 계획 업무 비율
- `docs/sprint/story-point-guide.md` — SP 산정 기준
- `docs/sprint/ticket-guide.md` — 티켓 작성 규칙

ARGUMENTS: $ARGUMENTS
