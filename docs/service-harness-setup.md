# 서비스 레포에 팀 하네스 연결하기

각 서비스 레포의 CLAUDE.md에 팀 하네스 참조를 추가하는 방법이다.

## 전제 조건

`./scripts/setup.sh`가 실행되어 `$TEAM2_HARNESS_PATH` 환경변수가 설정되어 있어야 한다.

---

## 방법 1: 기존 CLAUDE.md가 있는 경우 (naru, max)

CLAUDE.md 상단에 아래 섹션을 추가한다:

```markdown
## 팀 하네스

> 이 서비스는 개발 2팀 하네스를 따른다.
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
- Git Flow: `feature/{이슈ID}` → `develop` → `release/*` → `master`
- 커밋: `[{이슈ID}] 작업 내용`
- DB/SP 변경 시 별도 승인 + 롤백 스크립트 필수
- 신규 코드에서 레거시 DB/SP 직접 접근 금지
```

---

## 방법 2: CLAUDE.md가 없는 경우 (bazaar, tobe, aasm)

`templates/service-harness/CLAUDE.md.tmpl`을 복사해서 서비스 정보를 채운다:

```bash
cp $TEAM2_HARNESS_PATH/templates/service-harness/CLAUDE.md.tmpl ./CLAUDE.md
# 그 후 {{플레이스홀더}}를 실제 값으로 교체
```

---

## 서비스별 예시

두 설치 방법 모두 아래 [실행 검증 계약 연결](#실행-검증-계약-연결)을 함께 적용한다.

### naru (기존 CLAUDE.md 있음)

`$TEAM2_WORKSPACE_PATH/naru/NaruServer/CLAUDE.md` 상단에 추가:

```markdown
## 팀 하네스

> 이 서비스는 개발 2팀 하네스를 따른다.

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
cd $TEAM2_WORKSPACE_PATH/bazaar/BazaarServer
cp $TEAM2_HARNESS_PATH/templates/service-harness/CLAUDE.md.tmpl ./CLAUDE.md
# 플레이스홀더 교체
```

### max (기존 CLAUDE.md 있음)

`$TEAM2_WORKSPACE_PATH/max-doc/CLAUDE.md` 상단에 동일한 팀 하네스 섹션 추가.
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

## 실행 검증 계약 연결

기존 계약이 있으면 그 파일을 유지한다. 없으면 서비스 repo에서 [실행 계약 템플릿](../templates/service-harness/VERIFICATION.md.tmpl)을 빈 경로에 복사한다. 아래 예시는 기존 파일이 있으면 덮어쓰지 않는다.

```bash
if [ ! -e docs/verification.md ]; then
  mkdir -p docs
  cp "$TEAM2_HARNESS_PATH/templates/service-harness/VERIFICATION.md.tmpl" docs/verification.md
fi
```

1. 서비스 repo의 실제 명령·사용자 경로·환경 제약으로 빈칸을 채운다. 실행 전까지 초안으로 유지한다.
2. 실행 준비 → 대상 확인 → 대표 기능 실행 → 증거 수집 → 소유 자원 정리 → 증거 재열람을 수행한다. [하네스 CLI 사례](verification/harness-links.md)처럼 관찰된 결과로 판정한다.
3. 실행한 계약만 [카탈로그 규격](../catalog/README.md#실제-실행-검증-계약)에 따라 `verification.runtime_contract`의 repo·상대 경로로 등록한다. 기존 `verification.status`는 빠른 루프 커버리지 의미를 유지한다.
4. 서비스의 CLAUDE.md와 AGENTS.md에 해당 계약 포인터를 연결한다. 기존 파일에는 포인터만 추가하고 본문을 덮어쓰지 않는다.

환경을 확보하지 못한 서비스는 제약과 초안 상태를 기록한다. 대표 기능 하나를 실행했다고 전체 기능 검증이나 배포 검증으로 보고하지 않는다.

---

## 확인 방법

서비스 레포에서 Claude Code를 실행하고:

```
이 서비스의 팀 하네스 정책을 확인해줘
```

Claude가 `$TEAM2_HARNESS_PATH/policies/`의 파일들을 읽어서 답하면 연결 성공이다.

Codex의 AGENTS 진입점도 같은 계약을 찾는지 확인한다. 실행 검증 계약의 수용은 파일 읽기 외에 위 실제 실행과 증거 재열람까지 필요하다.
