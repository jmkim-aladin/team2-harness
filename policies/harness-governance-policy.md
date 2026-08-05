# 하네스 거버넌스 정책

하네스(팀 repo) 자체의 유지보수 규칙 — 언제 감사하고, 누가 판정하고, 어떻게 기록하는가.
실행 절차는 [`/ad:harness-optimize`](../.claude/commands/ad/harness-optimize.md), 지시문 해석·강도 기준은 [instruction-precedence-policy.md](./instruction-precedence-policy.md).

## 주기

- **스프린트 마감 주간 1회**: `/ad:harness-optimize 스킬` + `제약` 모드 실행. 결과는 [docs/skill-audit-baseline.md](../docs/skill-audit-baseline.md)에 회차 기록
- **수시 (실수 발생 시)**: AI·사람 실수 → 원인 분석(빠진 규칙 / 반복 업무 / 위험 행동 / 컨텍스트 부족) → 해당 정책·스킬·가드레일 즉시 보강. 상세: [ai-usage-policy.md](./ai-usage-policy.md) §하네스 개선 루프
- **KB 동기화**: 전사 KB 변경을 인지한 시점에 `동기화` 모드

## 권한

- 에이전트는 **제안까지** — 판정·머지는 사람
- 강도 하향(반드시→기본)·invariant/policy 등급 변경은 review-required ([instruction-precedence-policy.md](./instruction-precedence-policy.md) §판단 경계)
- 스킬 신설·삭제는 사용자 확인 후, Codex alias 동반 생성/삭제 ([skill-authoring-principles.md](./skill-authoring-principles.md) 대전제)

## 기록

- 감사 실행 결과는 audit-baseline 갱신 필수 — 날짜, 판정, 다음 회차 이관 항목
- **기각 결정**은 재논의 방지 형식으로 남긴다: 이유 + 탈출구(대안 경로) + 유발 사건/요청
- 실패 사례로 생긴 하드 게이트에는 `근거:` 일자를 붙인다

## 변경 통제

- 하네스 변경은 PR 경유 — 하네스 예외 브랜치 `team2/{작업-slug}` ([branching-strategy.md](./branching-strategy.md))
- 스킬 재표현·문장 삭제는 **삭제 테스트** 동반: 변경 전후 해당 스킬 1회 실행 비교, 같으면 확정
- 중복 제거 원칙: SoT 내용은 유지 / 참조 파일은 본문 삭제 후 링크 교체 / 요약이 필요하면 3줄 이내 + 링크 / 스킬 파일은 실행에 필요한 최소 정보만

## Source of Truth 등록부

각 주제는 하나의 SoT만 가진다. 새 SoT 주제가 생기면 이 표에 등록하고, 참조하는 파일에는 링크만 둔다.

| 주제 | Source of Truth | 참조하는 파일들 |
|------|----------------|----------------|
| **5W1H 작성법** | `docs/sprint/ticket-guide.md` 3항 | `.claude/commands/ad/ticket.md`, `templates/ticket-templates/`, `youtrack/ticket-guide.md` |
| **스토리 포인트** | `docs/sprint/story-point-guide.md` | `.claude/commands/ad/ticket.md`, `docs/sprint/sprint-planning-overview.md` |
| **이월 절차** | `docs/sprint/plan-change-process.md` | `docs/sprint/ticket-guide.md` 7항 (요약+링크만) |
| **맨데이 배분** | `docs/sprint/sprint-planning-overview.md` | - |
| **전사 상태 플로우** | `youtrack/ticket-guide.md` | `docs/sprint/ticket-guide.md` 8항 (링크만) |
| **OKR (팀/개인)** | Obsidian vault `wiki/processes/okr/` | `.claude/commands/ad/okr.md` |
| **서비스 프로파일** | `catalog/*.yaml` | `.claude/commands/ad/ticket.md` |
| **팀원 정보** | `policies/team-members.md` | `.claude/commands/ad/ticket.md`, `.claude/commands/ad/okr.md`, `.claude/commands/ad/weekly-report.md`, `.claude/commands/ad/capacity-plan.md`, `.claude/commands/ad/sprint-close-check.md`, `.claude/commands/ad/weekly-planned.md` |
| **티켓 산출물 frontmatter** | vault `wiki/guides/frontmatter-spec.md` | `.claude/commands/ad/ticket.md`, `.claude/commands/ad/new-note.md`, `.claude/commands/ad/weekly-report.md`, `.claude/commands/ad/sprint-close-check.md` (전부 링크만) |
| **지시 강도·우선순위** | `policies/instruction-precedence-policy.md` | CLAUDE.md, `policies/skill-authoring-principles.md`, `.claude/commands/ad/harness-optimize.md` (전부 링크만) |
| **DB/SP 첨부물 (PR 단계)** | `policies/code-review-policy.md` | engineering/legacy-modernization/gstack-override-policy, templates (링크만) |
| **DB/SP 첨부물 (배포 단계)** | `policies/release-policy.md` | 동일 |
| **시크릿 취급 공통 원칙** | `policies/security-policy.md` §취급 공통 원칙 | aws-secrets-convention, local-credentials-policy, datadog-api-policy (링크만) |
