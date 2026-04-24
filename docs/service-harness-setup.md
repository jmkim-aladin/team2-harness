# 서비스 레포에 팀 하네스 연결하기

각 서비스 레포의 CLAUDE.md에 팀 하네스 참조를 추가하는 방법입니다.

## 전제 조건

`./scripts/setup.sh`가 실행되어 `$TEAM2_HARNESS_PATH` 환경변수가 설정되어 있어야 합니다.

---

## 방법 1: 기존 CLAUDE.md가 있는 경우 (naru, max)

CLAUDE.md 상단에 아래 섹션을 추가합니다:

```markdown
## 팀 하네스

> 이 서비스는 개발 2팀 하네스를 따릅니다.
> 작업 전 팀 하네스의 관련 정책을 확인하세요.

| 정책 | 파일 |
|------|------|
| 엔지니어링 총칙 | `$TEAM2_HARNESS_PATH/policies/engineering-policy.md` |
| 브랜치/커밋 규칙 | `$TEAM2_HARNESS_PATH/policies/branching-strategy.md` |
| 코드 리뷰 기준 | `$TEAM2_HARNESS_PATH/policies/code-review-policy.md` |
| 배포/릴리즈 | `$TEAM2_HARNESS_PATH/policies/release-policy.md` |
| AI 사용 원칙 | `$TEAM2_HARNESS_PATH/policies/ai-usage-policy.md` |
| 현대화 정책 | `$TEAM2_HARNESS_PATH/policies/legacy-modernization-policy.md` |
| 보안 | `$TEAM2_HARNESS_PATH/policies/security-policy.md` |
| 장애 대응 | `$TEAM2_HARNESS_PATH/policies/incident-response.md` |
| 팀원/담당자 | `$TEAM2_HARNESS_PATH/policies/team-members.md` |
| 이 서비스 프로파일 | `$TEAM2_HARNESS_PATH/catalog/{서비스ID}.yaml` |

### 핵심 규칙
- Git Flow: `feature/DEV2-{번호}` → `develop` → `release/*` → `master`
- 커밋: Conventional Commits (`feat(scope): 🟩 DEV2-123 제목`)
- DB/SP 변경 시 별도 승인 + 롤백 스크립트 필수
- 신규 코드에서 레거시 DB/SP 직접 접근 금지
```

---

## 방법 2: CLAUDE.md가 없는 경우 (bazaar, tobe, aasm)

`templates/service-harness/CLAUDE.md.tmpl`을 복사해서 서비스 정보를 채웁니다:

```bash
cp $TEAM2_HARNESS_PATH/templates/service-harness/CLAUDE.md.tmpl ./CLAUDE.md
# 그 후 {{플레이스홀더}}를 실제 값으로 교체
```

---

## 서비스별 예시

### naru (기존 CLAUDE.md 있음)

`/Users/user/Documents/workspace/naru/NaruServer/CLAUDE.md` 상단에 추가:

```markdown
## 팀 하네스

> 이 서비스는 개발 2팀 하네스를 따릅니다.

| 정책 | 파일 |
|------|------|
| 엔지니어링 총칙 | `$TEAM2_HARNESS_PATH/policies/engineering-policy.md` |
| 브랜치/커밋 규칙 | `$TEAM2_HARNESS_PATH/policies/branching-strategy.md` |
| 코드 리뷰 기준 | `$TEAM2_HARNESS_PATH/policies/code-review-policy.md` |
| 배포/릴리즈 | `$TEAM2_HARNESS_PATH/policies/release-policy.md` |
| AI 사용 원칙 | `$TEAM2_HARNESS_PATH/policies/ai-usage-policy.md` |
| 보안 | `$TEAM2_HARNESS_PATH/policies/security-policy.md` |
| 서비스 프로파일 | `$TEAM2_HARNESS_PATH/catalog/naru.yaml` |
| 팀원 | `$TEAM2_HARNESS_PATH/policies/team-members.md` |
```

### bazaar (CLAUDE.md 없음)

```bash
cd /Users/user/Documents/workspace/bazaar/BazaarServer
cp $TEAM2_HARNESS_PATH/templates/service-harness/CLAUDE.md.tmpl ./CLAUDE.md
# 플레이스홀더 교체
```

### max (기존 CLAUDE.md 있음)

`/Users/user/Documents/workspace/max-doc/CLAUDE.md` 상단에 동일한 팀 하네스 섹션 추가.
max는 레거시이므로 현대화 정책 참조도 중요:

```markdown
| 현대화 정책 | `$TEAM2_HARNESS_PATH/policies/legacy-modernization-policy.md` |
| 현대화 계획 | `$TEAM2_HARNESS_PATH/catalog/max.yaml` (modernization 섹션) |
```

### tobe (CLAUDE.md 없음)

max와 동일하게 레거시 정책 참조 포함.

### aasm (CLAUDE.md 없음)

신규 서비스이므로 현대화 정책은 Observe 수준.

---

## 자동화 (향후)

`/ad:team2-onboard` 스킬이 구현되면 아래 명령으로 자동 생성 가능:

```
/ad:team2-onboard naru      # 기존 CLAUDE.md에 팀 하네스 섹션 추가
/ad:team2-onboard bazaar    # CLAUDE.md 새로 생성
```

---

## 확인 방법

서비스 레포에서 Claude Code를 실행하고:

```
이 서비스의 팀 하네스 정책을 확인해줘
```

Claude가 `$TEAM2_HARNESS_PATH/policies/`의 파일들을 읽어서 답하면 연결 성공입니다.
