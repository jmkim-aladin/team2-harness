# YouTrack KB → 하네스 동기화

전사 KB 문서가 업데이트되었을 때, 하네스 정책 파일을 최신 상태로 갱신합니다.

## 사용법

```
/ad:team2-kb-sync                    # 등록된 전사 KB 문서 전체 확인
/ad:team2-kb-sync REF-A-625          # 특정 문서 확인 후 하네스 갱신
```

## 실행 지침

1. 대상 KB 문서를 YouTrack API로 조회하여 최신 내용 확인
2. 연결된 하네스 정책 파일과 내용 비교
3. 차이가 있으면 사용자에게 변경 사항 요약 표시
4. 사용자 확인 후 하네스 정책 파일 갱신

## 전사 KB ↔ 하네스 매핑

| KB 문서 | 하네스 파일 |
|---------|------------|
| `REF-A-625` (Git Flow) | `policies/branching-strategy.md` |
| `REF-A-1958` (Clean Architecture) | `policies/engineering-policy.md` |
| `REF-A-3131` (Backend Environment) | 서비스 카탈로그 (naru, bazaar) |
| `REF-A-3133` (Frontend Environment) | 서비스 카탈로그 (max-front, maxcms-front) |

## API 접근

```bash
TOKEN="$YOUTRACK_TOKEN"
BASE="$YOUTRACK_BASE_URL"  # 기본: https://aladincommunication.youtrack.cloud

# KB 문서 조회
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/articles/{articleId}?fields=id,idReadable,summary,content,updated"
```

## 출력 형식

```
## KB 변경 감지: REF-A-625 (Git Flow)
- KB 최종 수정: 2026-03-25
- 하네스 파일: policies/branching-strategy.md

### 변경 사항 요약
- [변경된 내용 요약]

→ 하네스 갱신하시겠습니까? (y/n)
```
