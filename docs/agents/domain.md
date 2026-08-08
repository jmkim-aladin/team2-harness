# Domain docs — 팀 배치

도메인 지식을 다루는 스킬(`domain-modeling`, `grill-with-docs`, `tdd`, `wayfinder`)이 따르는 팀 배치. 원본 스킬의 repo 루트 `CONTEXT.md` 관례 대신 **vault가 도메인 지식의 집**이다 ([knowledge-base-policy.md](../../policies/knowledge-base-policy.md) — repo는 "어떻게 일하나", vault는 "무엇을 일하나").

## 위치

| 종류 | 위치 | 형식 |
|---|---|---|
| **용어집** | vault `wiki/glossary/{term}.md` — 용어당 한 파일 | 정의 1~2문장 + `_금지 동의어_` 목록 + 해소된 중의성 기록. 구현 디테일 금지 |
| **ADR / 결정** | vault `wiki/services/{서비스}/decisions/{slug}.md` | [engineering-policy.md](../../policies/engineering-policy.md) §ADR — 3조건(되돌리기 어려움 + 미래 의문 + 실제 트레이드오프) 모두 충족 시만 |
| 서비스 기술 컨텍스트 | harness `catalog/{서비스}.yaml` | 읽기 전용 참조 |

`repo 루트에 CONTEXT.md를 만들지 않는다.` `CONTEXT-MAP.md`도 만들지 않는다 — vault glossary 하나로 통일하고 wikilink로 연결한다.

## 소비 규칙

- 탐색 전에 대상 영역의 glossary 용어와 decisions를 읽는다. 없으면 조용히 진행 — 존재를 지적하거나 미리 만들자고 제안하지 않는다
- 출력(이슈 제목, 노트, 테스트 이름)에는 glossary의 canonical 용어를 쓴다. `_금지 동의어_`로 표류하지 않는다
- 필요한 개념이 glossary에 없으면: 프로젝트가 안 쓰는 언어를 발명 중이거나(재고) 실제 공백(용어 해소 시 lazy 생성)
- 기존 결정과 모순되는 출력은 조용히 덮지 말고 명시한다: "_{decisions 문서}와 상충 — 재검토 근거는 …_"

## 생성 규칙 (lazy)

용어가 대화에서 **해소되는 순간** `wiki/glossary/{term}.md`를 만든다 — 모아서 나중에 쓰지 않는다. 파일명은 kebab-case, H1은 canonical 용어. daily·티켓 노트에서 wikilink로 참조한다.
