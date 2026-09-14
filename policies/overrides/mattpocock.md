# mattpocock/skills 오버라이드 정책

[vendor/mattpocock/](../../vendor/mattpocock/) 스킬 사용 시 팀 규칙이 원본보다 우선한다. gstack의 [gstack-override-policy.md](../gstack-override-policy.md)와 같은 계층.

- 원본: [mattpocock/skills](https://github.com/mattpocock/skills) v1.2.3 (`6acc160e`), MIT
- 설치: 17종 vendor (2026-08-09 teach·wait-what 추가 — 최초 채택 시 판정 누락분 정정, 이로써 upstream promoted 25종 전수 판정: 설치 17 + 제외 8) (repo에 고정, `setup_harness.py`가 링크). 설치 목록·제외 목록은 [harness.manifest.json](../../harness.manifest.json)이 SoT

## 제외 8종과 이유

| 스킬 | 이유 | 팀 대체 |
|---|---|---|
| `code-review` | 팀 것이 더 성숙 (범위 한정·게시 규격·교차검증) | `/ad:code-review` |
| `to-spec` / `to-tickets` | spec은 YouTrack 5W1H, 분할은 팀 규칙 | `/ad:ticket` |
| `setup-matt-pocock-skills` | CLAUDE.md를 직접 편집 — 팀 SoT 체계와 충돌 | `docs/agents/*.md` 직접 작성 (완료) |
| `triage` | 팀 접수 흐름과 라벨 체계 상이 | `/ad:work-prep` |
| `ask-matt` | 라우터 중복 | [harness-guide.md](../../docs/harness-guide.md) §작업 플로우 |
| `writing-for-agents` | 번안 완료 | [skill-authoring-principles.md](../skill-authoring-principles.md) |
| `improve-codebase-architecture` | 기능 중복 | `/ad:architecture-analysis` |

superpowers 대체: `brainstorming` → `/ad:grill`, `systematic-debugging` → `diagnosing-bugs`, `executing-plans`·`test-driven-development` → `/ad:implement`+`tdd`.

**동사층 wrapper**: `grill-with-docs`·`grill-me`·`implement`는 링크하지 않고 `/ad:grill`·`/ad:implement`가 진입점이다 (메뉴 이중화 방지, [skill-authoring-principles.md](../skill-authoring-principles.md) §구조). vendor 사본은 SoT로 유지.

## 오버라이드 규칙

- **커밋·푸시 사용자 확인** (INVARIANT) — `implement`가 "commit your work"라 해도 커밋 전 확인. 형식 `[{이슈ID}] 작업 내용`, AI footer 금지
- **spec의 거처** — YouTrack Feature 본문(5W1H). 별도 spec 파일 생성 금지
- **도메인 문서 위치** — [docs/agents/domain.md](../../docs/agents/domain.md). repo 루트 CONTEXT.md 생성 금지
- **이슈 트래커** — [docs/agents/issue-tracker.md](../../docs/agents/issue-tracker.md)
- **리뷰** — `implement` 마감 리뷰는 `/ad:code-review` (사용자 호출 — 게시 시점은 사람이 정한다). 내장 `/code-review`가 이름을 선점하므로 주의
- **research 산출물** — [knowledge-base-policy.md](../knowledge-base-policy.md) 결정 트리 적용 (vault/repo 판정)
- **smart zone 상수** — 원본의 ~150k·"세션당 티켓 1개"는 구모델 기준 보수치. 규율은 지키되 수치는 참고치
- **수직 슬라이스** — 개발 Task 내부 분할에만. 팀 단계 분리(개발/검증/배포)가 우선

## 디버깅 — 반복 실패의 공통 전제

`diagnosing-bugs`의 복수 가설·반증·계측 루프에 적용한다. 같은 전제에 기대는 서로 다른 수정이 같은 재현 검사에서 반복 실패하면, 다음 수정 전에 공통 전제를 한 문장으로 적는다.

- 편중·누수·경합 문제라면 작업자·세션·인스턴스별 상태나 자원 분포를 측정하고, 특정 대상에 역할을 배정하는 구조를 확인한다.
- 관찰이 예측과 다르면 전제를 바꾼다. 한 원인의 임계값·재시도 횟수만 계속 조정하지 않는다.
- 횟수만으로 사용자에게 질문하거나 작업을 중단하는 규칙은 아니다. 자원 분포 측정은 해당 증상에서만 사용한다.

## 완료·인계 증거

`implement`·`handoff`의 완료 보고와 재개 지점은 [검증 증거 계약](../../docs/agents/verification.md)에 연결한다. 기존 spec·진행 기록·evidence를 참조하고 별도 일지를 중복 생성하지 않는다.

## vendored 사본의 upstream 대비 diff (포인터 편집 등록부)

vendor 사본에 가한 편집은 아래 전부다. 재동기화 시 이 표만 재적용한다.

| 파일 | 편집 |
|---|---|
| `implement/SKILL.md` | 리뷰를 `/ad:code-review`로, 커밋 전 사용자 확인 — 포인터 1줄 |
| `domain-modeling/SKILL.md` | 파일 위치를 `docs/agents/domain.md`로 — 포인터 1줄 |
| `diagnosing-bugs/SKILL.md` | 사후 아키텍처 핸드오프를 `/ad:architecture-analysis`로 — 포인터 1줄 |
| `handoff/SKILL.md` | 완료·인계 전에 이 오버라이드와 증거 계약을 읽는 포인터 1줄 |
| `wait-what/SKILL.md` | 어휘 원천을 `CONTEXT.md` → 팀 용어집(docs/agents/domain.md)으로 — 포인터 1줄 |

## 재동기화 절차

```bash
git clone --branch <새태그> --depth 1 https://github.com/mattpocock/skills /tmp/mp
# manifest install 목록만 vendor/mattpocock/ 에 복사
# 위 diff 등록부의 포인터 편집 재적용
# manifest pin 갱신 → PR (변경 스킬은 거버넌스 §변경 통제의 삭제 테스트)
```

CHANGELOG 확인 주기는 [harness-governance-policy.md](../harness-governance-policy.md) §주기의 스택 감사(월 1회)에 포함.
