# YouTrack 티켓 생성

사용자 요청을 기반으로 5W1H 형식의 YouTrack 티켓을 생성합니다.

## 기본값

- **프로젝트**: DEV2
- **담당자**: 대상 서비스의 owner를 `policies/team-members.md`에서 참조 (없으면 사용자에게 질문)
- **유형**: Task
- **Phase**: Backlog (ToBe)
- **우선순위**: 보통 (Normal)

## 참조 문서 (Source of Truth)

티켓 작성 시 아래 하네스 문서를 **반드시 읽어서** 규칙을 준수합니다.

| 문서 | 경로 | 참조 항목 |
|------|------|-----------|
| **티켓 작성 가이드** | `docs/sprint/ticket-guide.md` | 5W1H 상세 작성법, 스프린트 상태, 티켓 크기 |
| **스토리 포인트 가이드** | `docs/sprint/story-point-guide.md` | SP 산정 기준 (1/2/3/5/8/13) |
| **스프린트 계획 운영** | `docs/sprint/sprint-planning-overview.md` | 운영/계획 업무 분류 |
| **업무 계획 변경 절차** | `docs/sprint/plan-change-process.md` | 긴급 요청·이월 처리 |
| **전사 상태 플로우** | `youtrack/ticket-guide.md` | YouTrack 상태 머신 (ToBe→Closed) |

### 핵심 규칙 요약

- **Feature ≤ 1주 / Task ≤ 1일** (초과 시 분할)
- **13점(XXL)은 스프린트 투입 금지** → 8점 이하로 분할 필수
- **예상 시작 일자 필수**
- **전월 마지막 주에 계획 완료**

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | YouTrack API 인증 토큰 |
| `$YOUTRACK_BASE_URL` | YouTrack 베이스 URL (기본: `https://aladincommunication.youtrack.cloud`) |

## 참조 정보

### YouTrack Knowledge Base 조회
티켓 작성 시 관련 KB 문서를 참조하여 컨텍스트를 보강합니다.

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$BASE/api/articles?\$top=10&fields=id,idReadable,summary,content,parentArticle(summary)&query=project:DEV2"
```

**DEV2 KB 구조:**
- `DEV2-A-1` (Team): 팀 운영 (온보딩, 서버접속, 보안, 장애대응, OKR, 스프린트)
- `DEV2-A-21` (Shared): 공유 문서 (만권당, 투비 등 서비스별)
- `DEV2-A-22` (Onboarding): 온보딩
- `DEV2-A-108`: 😺만권당

### 서비스 카탈로그 참조
- 위치: `catalog/` (max, tobe, naru, bazaar, aasm)

### 팀원 정보
- 위치: `policies/team-members.md`
- 서비스별 owner/backup 정보로 담당자 자동 제안

## 실행 지침

사용자가 `/ad:ticket` 또는 `/ad:ticket [설명]`을 입력하면:

1. **`docs/sprint/ticket-guide.md`를 읽어** 5W1H 작성법과 최신 규칙을 확인
2. 사용자 입력이 있으면 해당 내용을 기반으로 티켓 작성
3. 사용자 입력이 없으면 어떤 티켓을 만들지 질문
4. **대상 서비스가 명확하면** 서비스 카탈로그(`catalog/*.yaml`)를 읽어 컨텍스트 보강
5. **관련 KB 문서가 있을 수 있으면** YouTrack KB API로 검색하여 참조 (선택적)
6. **담당자**는 서비스별 owner를 기본값으로 제안
7. **SP 산정**: `docs/sprint/story-point-guide.md` 기준표에 따라 산정 제안

## 티켓 출력 형식

```
## 티켓 정보
- **담당자**: {서비스 owner} ({이름})
- **유형**: Task
- **Phase**: Backlog (ToBe)
- **우선순위**: 보통 (Normal)
- **스토리 포인트**: {1|2|3|5|8} (산정 근거: 복잡도/불확실성/작업량)
- **예상 시작 일자**: {YYYY-MM-DD}
- **OKR 연계**: {팀 KR 번호} (해당 시, docs/okr/ 참조)

---

(5W1H 본문은 docs/sprint/ticket-guide.md 3항의 형식을 따름)

* ### What (무엇을 할 것인가)
* ### Why (왜 필요한가)
* ### Who (누가 사용할 것인가)
* ### When (언제 수행/발생하는가)
* ### Where (어디에 적용되는가)
* ### How (어떻게 구현할 것인가)
```

## 후속 작업 안내

티켓 초안 작성 후 사용자에게 안내:
1. 내용 검토 및 수정 요청 여부 확인
2. 확인되면 YouTrack MCP(`mcp__youtrack__create_issue`)로 직접 생성 제안
3. KB 참조 문서가 있으면 티켓 설명에 링크 포함

ARGUMENTS: $ARGUMENTS
