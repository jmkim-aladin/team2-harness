---
description: 계획 수립 — 구상·grill 결과를 vault 계획 노트로 합성. "계획 세워줘", "로드맵 잡자", 다세션 프로젝트 착수에
---

# 계획 (plan)

구상이나 `/ad:grill` 세션 결과를 **vault 계획 노트**로 합성한다. 인터뷰는 하지 않는다 — 정렬이 안 됐으면 먼저 `/ad:grill`.

## 자리 (경계 — 중요)

- **티켓 전 단계** 전용: 다세션 프로젝트, 아직 익지 않은 구상, 현대화 트랙처럼 티켓 여러 개를 낳을 계획
- **spec이 아니다**: 티켓을 발행하는 순간 그 범위의 SoT는 YouTrack 5W1H다 — 계획 노트에는 티켓 링크를 남기고 해당 절의 상세를 티켓으로 넘긴다 (이중 유지 금지)
- 단일 티켓감이면 계획 노트를 만들지 말고 바로 `/ad:ticket`을 안내한다

## 산출 위치 (knowledge-base-policy 결정 트리)

| 성격 | 경로 | frontmatter |
|---|---|---|
| 특정 서비스 구상 | `$LOCAL_WIKI_PATH/wiki/services/{서비스ID}/proposals/{kebab-slug}.md` | `type: proposal` — [work-prep 노트 템플릿](../../../docs/sprint/work-prep-note-template.md) §자유글 |
| 프로젝트급 (서비스 횡단·신규) | `$LOCAL_WIKI_PATH/wiki/projects/{kebab-slug}/plan.md` | `type: project` — `templates/vault-notes/project.md` |

## 본문 골격

1. **목표** — 도달 상태 한 문장 (wayfinder의 Destination과 같은 규율)
2. **배경·결정된 것** — grill에서 확정된 결정들 (용어는 vault 용어집 canonical로)
3. **미결** — 아직 안개인 것 (wayfinder의 Not-yet-specified처럼 — 억지로 쪼개지 않는다)
4. **단계** — 마일스톤. 각 단계는 티켓화 후보이며, 발행 시 `[[dev2-XXXX]]` 링크로 교체
5. **다음 행동** — 첫 단계의 착수 지점

세션보다 큰 안개 과제(결정 자체가 다수 미결)면 계획 노트 대신 `/wayfinder`를 제안한다 — plan은 길이 보이는 계획, wayfinder는 길 찾기.

## 게이트

- 노트 신규 생성: 경로 + frontmatter 미리보기 출력 후 바로 작성 (work-prep 관례)
- daily 아젠다에 한 줄 추가 (idempotent)
- YouTrack·KB·git 무변경. 티켓화는 사용자가 `/ad:ticket`으로

ARGUMENTS: $ARGUMENTS
