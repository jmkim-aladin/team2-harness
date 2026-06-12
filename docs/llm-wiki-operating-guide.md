# LLM 위키 운영 가이드

이 문서는 개발 2팀 Obsidian vault를 LLM이 실행 전후에 참조할 수 있는 운영 메모리로 유지하기 위한 하네스 기준이다.

## 저장소 경계

- 팀 하네스: 위키 구조, 관계 필드, lint, 자동 생성 규칙의 source of truth.
- Obsidian vault: 프로젝트 진행, 티켓 산출물, 회의록, daily, OKR, 도메인 분석 같은 실제 업무 내용의 source of truth.

즉, 실행 시 에이전트가 따라야 하는 관계 규칙은 하네스에 두고, 개별 노트의 내용과 연결 결과는 vault에 둔다.

## 목표

LLM 위키의 목표는 문서를 많이 저장하는 것이 아니라, 에이전트가 다음 질문에 근거 있게 답할 수 있게 하는 것이다.

- 이 티켓을 지금 착수할 수 있는가?
- 이 서비스의 현재 리스크와 결정 대기 항목은 무엇인가?
- 이 회의가 어떤 티켓, OKR, 서비스와 연결되는가?
- 오늘 사람이 결정해야 할 항목은 무엇인가?
- 실행 결과를 어떤 증거로 완료 처리할 수 있는가?

## 핵심 원칙

- Entity-first: 폴더 위치보다 `service`, `ticket`, `meeting`, `okr`, `domain`, `decision`, `project` 엔티티 연결을 우선한다.
- Provenance: 자동 추론, Granola, YouTrack, 코드, 하네스, 사람 기록의 출처와 신뢰도를 구분한다.
- Projection: 서비스/프로젝트/daily 같은 허브 노트에 관련 노트를 역방향으로 모아 실행 전 읽기 화면을 만든다.
- Reviewable automation: 자동화는 관계 후보를 만들고, 사람이 확인하면 `confirmed`로 승격한다.

## 표준 관계 필드

원천 식별자는 기계 처리용으로 유지한다.

```yaml
service_id: storefront
ticket_id: DEV2-5283
granola_id: not_xxx
```

그래프 간선은 Tolaría/Obsidian/LLM이 읽기 쉬운 wikilink 필드로 둔다.

```yaml
related_services:
  - "[[storefront]]"
related_tickets:
  - "[[dev2-5283]]"
related_okrs:
  - "[[2026-q2-kimjeongmin]]"
related_meetings:
  - "[[2026-06-05-order-and-payment-process-review]]"
related_domains:
  - "[[order]]"
related_projects:
  - "[[agentic-os]]"
relation_status: inferred | confirmed
relation_sources:
  - granola
  - youtrack
  - manual
```

`relation_status`는 관계 필드 전체의 기본 상태다. 필드별 출처가 필요해지면 `relation_sources`에 간단한 근거를 추가한다.

## 타입별 최소 연결

| type | 최소 연결 |
|---|---|
| `ticket` | `service` 또는 `related_services`; 가능하면 `related_okrs`, `related_domains`, `related_meetings` |
| `meeting` | `related_services` 또는 `related_tickets` 중 하나. 일반 회의는 `scope: general` 허용 |
| `okr` | `related_tickets`, `related_services`, `related_projects` |
| `daily` | 그날의 `related_tickets`, `related_meetings` |
| `weekly-report` | 주간 `related_tickets`, `related_services`, `related_okrs` |
| `analysis` / `decision` / `proposal` | `service_id`, `related_tickets`, `related_domains` |
| `project` | `related_services`, `related_tickets`, `related_okrs` |

## 자동 보강 규칙

초기 자동화는 deterministic 추론만 적용한다.

- 본문 또는 frontmatter의 `DEV2-\d+` → `related_tickets`
- 티켓 노트의 `service` / `service_id` → `related_services`
- OKR 본문에 적힌 DEV2 티켓 → `related_tickets`
- daily의 `## 회의` wikilink → `related_meetings`
- Granola 회의 제목/요약의 서비스 키워드 → `related_services` 후보

자동 추론 결과는 `relation_status: inferred`로 저장한다. 사람이 검토하면 `confirmed`로 변경한다.

## Projection

서비스 노트는 관련 노트의 허브여야 한다. `generate_vault_indexes.py` 또는 별도 relation generator는 서비스 노트에 다음 generated block을 만든다.

```markdown
<!-- generated:related-notes source=vault-relations updated=YYYY-MM-DD -->
## 관련 티켓
- [[dev2-5283]]

## 관련 회의
- [[2026-06-05-order-and-payment-process-review|주문/결제 프로세스 검토]]

## 관련 OKR
- [[2026-q2-kimjeongmin]]

## 관련 결정
- (없음)
<!-- /generated -->
```

generated block만 자동 갱신하고, 사람이 작성한 서비스 요약과 판단은 보존한다.

## 품질 지표

정기 audit은 다음을 집계한다.

- type별 관계 필드 누락률
- 깨진 wikilink 수
- `meeting` 중 서비스/티켓/scope가 모두 없는 비율
- `okr` 중 `related_tickets`가 없는 비율
- `ticket` 중 서비스 연결이 없는 비율
- `inferred` 상태로 7일 이상 남은 관계 수

## 권장 도구

- `tools/audit_vault_relations.py`: 관계 누락률과 후보 리포트 생성
- `tools/enrich_vault_relations.py`: deterministic 관계 backfill
- `tools/lint_vault.py`: 깨진 링크와 최소 관계 규칙 검사 확장
- `tools/generate_vault_indexes.py`: 서비스/프로젝트 허브 projection 생성 확장

## 관련

- `policies/knowledge-base-policy.md`
- `docs/wiki-navigation-guide.md`
- vault `wiki/guides/frontmatter-spec.md`
- vault `wiki/projects/agentic-os/agentic-os.md`
