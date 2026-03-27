# CLAUDE.md 작성 정책

## 원칙

CLAUDE.md는 **최소한으로** 유지합니다. 팀 공통 정책은 팀 하네스에서 관리하고, 서비스 CLAUDE.md에는 중복 기재하지 않습니다.

## 서비스 CLAUDE.md에 넣어야 하는 것

1. **팀 하네스 참조** (2줄)
2. **서비스 개요** (스택, DB, 배포 — 간략히)
3. **빌드/테스트/실행 명령** (복사해서 바로 실행 가능하게)
4. **주요 디렉토리 구조** (코드 탐색용)
5. **서비스 고유 금지 사항** (팀 공통이 아닌 것만)

## 서비스 CLAUDE.md에 넣지 않는 것

- 팀 정책 (브랜치, 코드리뷰, 배포, AI 사용 등) → `$TEAM2_HARNESS_PATH/policies/`
- 팀원/담당자 → `$TEAM2_HARNESS_PATH/policies/team-members.md`
- 서비스 상세 메타데이터 → `$TEAM2_HARNESS_PATH/catalog/{서비스}.yaml`
- 현대화 계획 → `$TEAM2_HARNESS_PATH/catalog/{서비스}.yaml`
- YouTrack/KB 정보 → 스킬로 조회

## 팀 하네스 참조 형식

```markdown
## 팀 하네스

개발 2팀 하네스: `$TEAM2_HARNESS_PATH/policies/` (정책), `$TEAM2_HARNESS_PATH/catalog/{서비스ID}.yaml` (서비스 프로파일)
브랜치: `feature/{이슈ID}` | 커밋: `[{이슈ID}] 작업 내용` | PR 전 squash 필수
```

레거시 서비스는 한 줄 추가:
```markdown
DB/SP 변경 시 별도 승인 + 롤백 필수 | 신규 코드에서 SP 직접 호출 금지
```

## 크기 기준

- 서비스 CLAUDE.md: **50줄 이하** 목표
- 팀 하네스 참조: 2~3줄
- 서비스 개요: 5줄 이내
- 빌드 명령: 실제 명령만
- 디렉토리 구조: 1단계만

> CLAUDE.md가 길어지면 → 팀 하네스로 옮기거나, 서비스 하네스 파일(AGENTS.md, RUNBOOK.md)로 분리
