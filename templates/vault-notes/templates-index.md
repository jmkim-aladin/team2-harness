---
type: index
title: 노트 템플릿
canonical_id: index:templates
status: canonical
updated_at: 2026-05-27
---

# 노트 템플릿

<!-- llm-hint -->
type별 frontmatter + 본문 스켈레톤. 새 노트 작성 시 `{{date}}` 등 placeholder 채워 사용.
Obsidian Templates plugin이 "Insert template"로 자동 삽입. `/ad:new-note` 스킬이 type 추정 후 본 디렉터리에서 적합 템플릿 읽어 사용.
templates/ 자체는 lint 예외 (스켈레톤 placeholder 포함).
<!-- /llm-hint -->

## 목록

- [[ticket|ticket]] — DEV2-* 티켓 산출물 (auto-prep/in-progress/done/backlog)
- [[meeting|meeting]] — 팀 회의록 (YYYY-MM-DD-topic.md)
- [[daily|daily]] — daily 노트 (YYYY-MM-DD.md, 오늘의 아젠다)
- [[weekly-report|weekly-report]] — 주간업무 보고서 초안
- [[okr|okr]] — 분기/연간 OKR (팀·개인)
- [[incident|incident]] — 장애 사례·post-mortem
- [[capacity-plan|capacity-plan]] — 월별 가용 맨데이·velocity
- [[analysis|analysis]] — 서비스 분석 (coverage/gap/audit/triage)
- [[decision|decision]] — 서비스 ADR
- [[proposal|proposal]] — 서비스 개선 후보·신청
- [[service-index|service-index]] — services/{svc}/{svc}-index.md
- [[domain-index|domain-index]] — services/{svc}/domains/{domain}/{domain}-index.md
- [[glossary|glossary]] — canonical 도메인 용어

## 사용

### Obsidian 안

1. 새 파일 생성 (적절한 dir 안)
2. Cmd+P → "Insert template" → type 선택
3. placeholder 채움

### CLI (수동)

```bash
cp "$VAULT/wiki/templates/{type}.md" "$VAULT/wiki/.../target.md"
# 그 다음 placeholder 채움
```

### `/ad:new-note`

자동 type 추정 + 적합 템플릿 적용 + frontmatter 자동 채움.

## placeholder 컨벤션

- `{{date}}` — 오늘 (YYYY-MM-DD)
- `{{title}}` — 노트 제목
- `{{user}}` — 본인 (YouTrack ID, 기본 jmkim)
- `{{service_id}}` — 서비스 id
- `{{ticket_id}}` — DEV2-NNNN
- `{{ ... }}` — 그 외 필드별
