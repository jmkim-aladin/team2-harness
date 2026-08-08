---
description: YouTrack KB 문서 조회
---

# YouTrack KB 문서 조회

YouTrack Knowledge Base에서 DEV2 프로젝트 문서를 조회한다.

## 사용법

```
/ad:team2-kb-read [검색어 또는 문서ID]
/ad:team2-kb-read 목록 [카테고리]     # 문서 트리만 표시
```

## 실행 지침

1. **문서 ID가 주어진 경우** (예: `DEV2-A-108`): 해당 문서 직접 조회
2. **검색어가 주어진 경우** (예: `만권당`, `배포`): KB에서 관련 문서 검색
3. **`목록`이 주어진 경우**: 본문 없이 트리만 표시. 카테고리 지정 시 그 하위만
4. **아무것도 없으면**: DEV2 KB 루트 구조 표시

트리는 항상 API 재조회 결과를 쓴다. 아래 구조표는 루트 식별용 참고값이며 스냅샷이다.

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

`목록` 모드는 본문을 빼고 트리만 출력한다.

```
카테고리명 (문서ID)
├─ 문서제목 (문서ID)
│  ├─ 하위문서 (문서ID)
```
