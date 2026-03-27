# YouTrack KB 문서 조회

YouTrack Knowledge Base에서 DEV2 프로젝트 문서를 조회합니다.

## 사용법

```
/ad:team2-kb-read [검색어 또는 문서ID]
```

## 실행 지침

1. **문서 ID가 주어진 경우** (예: `DEV2-A-108`): 해당 문서 직접 조회
2. **검색어가 주어진 경우** (예: `만권당`, `배포`): KB에서 관련 문서 검색
3. **아무것도 없으면**: DEV2 KB 루트 구조 표시

## API 접근

```bash
TOKEN="$YOUTRACK_TOKEN"
BASE="$YOUTRACK_BASE_URL"  # 기본: https://aladincommunication.youtrack.cloud

# 문서 ID로 조회
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/articles/{articleId}?fields=id,idReadable,summary,content,parentArticle(idReadable,summary),childArticles(idReadable,summary),created,updated,reporter(name)"

# 프로젝트 문서 목록 (검색)
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/admin/projects/DEV2/articles?\$top=50&fields=id,idReadable,summary,parentArticle(idReadable,summary)"

# 하위 문서 조회
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/articles/{articleId}/childArticles?fields=idReadable,summary"
```

## DEV2 KB 구조

| ID | 이름 | 설명 |
|----|------|------|
| `DEV2-A-1` | Team | 팀 운영 (온보딩, 서버접속, 보안, 장애대응, OKR, 스프린트) |
| `DEV2-A-21` | Shared | 공유 문서 (서비스별 문서) |
| `DEV2-A-22` | Onboarding | 온보딩 |
| `DEV2-A-108` | 😺만권당 | 만권당 관련 (Shared 하위) |

## 출력 형식

문서 조회 결과를 마크다운으로 정리하여 표시:
- 문서 제목 + ID
- 상위 문서 경로
- 본문 내용
- 하위 문서 목록 (있으면)
