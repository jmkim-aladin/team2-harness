# YouTrack KB 문서 목록 조회

YouTrack Knowledge Base DEV2 프로젝트의 문서 구조를 트리 형태로 표시합니다.

## 사용법

```
/ad:team2-kb-list              # 전체 루트 카테고리
/ad:team2-kb-list [카테고리]    # 특정 카테고리 하위 문서
```

## 실행 지침

1. **인자 없음**: DEV2 KB 루트 3개 카테고리와 각 하위 문서 표시
2. **카테고리 지정**: 해당 카테고리의 하위 문서 트리 표시

## API 접근

```bash
TOKEN="$YOUTRACK_TOKEN"
BASE="$YOUTRACK_BASE_URL"  # 기본: https://aladincommunication.youtrack.cloud

# DEV2 프로젝트 전체 문서 (루트 식별용)
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/admin/projects/DEV2/articles?\$top=100&fields=id,idReadable,summary,parentArticle(id,idReadable,summary)"

# 특정 문서의 하위 조회
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/articles/{articleId}?fields=idReadable,summary,childArticles(idReadable,summary)"
```

## DEV2 KB 루트 구조

```
DEV2 KB
├─ Team (DEV2-A-1)
│  ├─ Onboarding (DEV2-A-2)
│  ├─ 팀 계정 관리 (DEV2-A-18)
│  ├─ 업무 필수 문서 (DEV2-A-89)
│  ├─ 서버접속 정보 (DEV2-A-152)
│  ├─ 보안 문서 관리 (DEV2-A-156)
│  ├─ AWS 표준 인프라 구성안 (DEV2-A-229)
│  ├─ 서버점검 (DEV2-A-257)
│  ├─ 서비스 장애대응 (DEV2-A-297)
│  ├─ OKR (DEV2-A-578)
│  ├─ 주간업무 (DEV2-A-692)
│  └─ Sprints (DEV2-A-785)
├─ Shared (DEV2-A-21)
│  └─ 😺만권당 (DEV2-A-108)
└─ Onboarding (DEV2-A-22)
```

## 출력 형식

트리 구조로 문서 목록 표시:
```
카테고리명 (문서ID)
├─ 문서제목 (문서ID)
│  ├─ 하위문서 (문서ID)
```
