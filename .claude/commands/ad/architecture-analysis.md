# DEV2 저장소 아키텍처 분석

저장소 전체를 근거 기반으로 분석해 설계 철학, 실제 실행 구조, Clean/Hexagonal/DDD 적합성, 운영 위험과 네이밍을 정리한다. Markdown 원본과 self-contained HTML Reader를 DEV2 로컬 wiki에 저장한다.

## 사용법

```text
/ad:architecture-analysis
/ad:architecture-analysis bazaar
/ad:architecture-analysis /absolute/path/to/repo
/ad:architecture-analysis --static-only
/ad:architecture-analysis bazaar --static-only
```

- 인자 없음: 현재 Git 저장소를 분석한다.
- `service_id`: 현재 저장소와 `catalog/{service_id}.yaml`을 대조한다. 일치하지 않으면 저장소 경로를 확인한다.
- 절대/상대 경로: 해당 Git 저장소를 분석한다.
- `--static-only`: compile/test를 실행하지 않고 정적 분석만 수행한다.

## 절대 규칙

- 분석 대상 소스 파일을 생성·수정·삭제하지 않는다.
- formatter, codegen, migration, package update, dependency install을 실행하지 않는다.
- git clean/reset/checkout/stash, commit, push, merge, PR을 실행하지 않는다.
- DB, 운영 API, 공급사·벤더 API, 배포 시스템을 호출하지 않는다.
- 토큰, 비밀번호, API key, connection string 값을 출력하거나 문서에 저장하지 않는다.
- 기존 dirty worktree를 그대로 보존하고 분석 기준에만 기록한다.
- build/test가 repo-tracked 파일을 바꾼 경우 즉시 중단하고 변경 파일을 사용자에게 알린다. 임의 복구하지 않는다.

## 환경과 기준 문서

```bash
HARNESS="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"
VAULT="${LOCAL_WIKI_PATH:-/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2}"
```

먼저 아래 문서를 읽는다.

1. `$HARNESS/policies/knowledge-base-policy.md`
2. `$HARNESS/policies/wiki-document-language-and-title-policy.md`
3. `$HARNESS/docs/architecture-analysis-guide.md`
4. `$VAULT/wiki/guides/document-placement.md`
5. `$VAULT/wiki/guides/frontmatter-spec.md`
6. 판별된 `$HARNESS/catalog/{service_id}.yaml`

대상 저장소의 `AGENTS.md`, `CLAUDE.md`, README, 아키텍처 문서도 실제 존재하는 것만 읽는다.

## 1. 대상 저장소와 서비스 판별

1. 경로 인자가 있으면 그 경로, 없으면 `git rev-parse --show-toplevel` 결과를 repo root로 사용한다.
2. `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git remote get-url origin`을 수집한다.
3. remote repository 이름과 `catalog/*.yaml`의 `repo`를 대조해 `service_id`를 찾는다.
4. 사용자가 service_id를 주면 catalog와 remote/path가 일치하는지 검증한다.
5. 0개 또는 여러 서비스가 일치하면 후보와 근거를 제시하고 사용자 확인 전에는 vault에 쓰지 않는다.
6. 날짜는 실행 환경의 `YYYY-MM-DD`, 기준 revision은 `git rev-parse --short=8 HEAD`를 사용한다.

## 2. 구조 복원

정확한 파일명이나 framework를 가정하지 말고 manifest와 entrypoint부터 찾는다. 검색은 `rg`, 파일 목록은 `rg --files`를 우선한다.

다음을 실제 코드에서 복원한다.

- 언어, framework, build system, runtime application
- module/package/project dependency graph
- inbound API, scheduler, consumer, CLI entrypoint
- Application/UseCase, Domain, Port, Adapter, persistence 경계
- 외부 시스템, 인증, secret, network, DB 경계
- Aggregate, 주요 상태, 상태 전이와 transaction 경계
- 수집→정규화→저장→발행→재처리 같은 핵심 데이터 흐름
- CI/CD, migration, 배포 중단·재개, 장애 복구 방식
- 테스트 분포와 실제 재현 가능성

모듈 이름만 보고 역할을 단정하지 않는다. build dependency와 import/call site를 교차 확인한다.

## 3. 철학과 아키텍처 평가

`docs/architecture-analysis-guide.md`의 rubric을 적용한다.

- 반복되는 코드 구조에서 **실제 철학**을 먼저 추론한다.
- README/문서에서 주장하는 **선언된 철학**은 별도로 기록한다.
- 둘의 차이를 `잘 맞음 / 실용적 타협 / 구조적 불일치 / 문서만 존재`로 분류한다.
- Clean Architecture, Hexagonal, DDD, CQRS를 폴더명만으로 판정하지 않는다.
- 보안, 인증·인가, transaction, concurrency, idempotency, retry, outbox, 배포, 테스트, 문서 drift를 함께 평가한다.
- 오타뿐 아니라 `UseCase`, `Coordinator`, `Manager`, `Helper`, `Adapter`, `Facade` 같은 역할 용어가 일관적인지 확인한다.

각 발견은 다음 정보를 갖는다.

| 필드 | 기준 |
|---|---|
| 우선순위 | P0 즉시 보안·데이터·배포 위험 / P1 높은 런타임·재현성 위험 / P2 구조적 부채 / P3 정리·가독성 |
| 근거 | 파일 경로와 line 또는 실행 명령 결과 |
| 영향 | 어떤 사용자·데이터·운영 흐름이 영향을 받는지 |
| 확신도 | 높음 / 중간 / 낮음 |
| 권장 방향 | 전체 재작성보다 현재 철학을 살리는 최소 안전 변경 |

근거 없는 선호를 아키텍처 위반으로 쓰지 않는다.

## 4. 검증 실행

`--static-only`가 아니면 manifest와 CI를 읽은 뒤 안전한 명령만 선택한다.

허용 예:

- Gradle/Maven compile, unit test, dependency report
- `dotnet build`, 외부 의존 없는 unit test
- Node typecheck, lint의 check-only 모드, unit test

금지 예:

- format/write 모드
- snapshot 갱신
- migration 실행
- Docker compose로 DB나 외부 서비스를 시작
- 실제 credentials가 필요한 integration/real test
- 배포·publish·package update

실행하지 못한 검증은 숨기지 말고 명령과 미실행 사유를 `검증과 한계`에 기록한다. 명령 실행 전후 `git status --short`를 비교한다.

## 5. Markdown 작성

template `$HARNESS/templates/architecture-analysis/report.md`를 사용한다. 모든 placeholder를 실제 값으로 치환하고 빈 섹션을 남기지 않는다.

필수 H2 제목은 renderer 계약이므로 정확히 유지한다.

1. `결론`
2. `분석 기준`
3. `아키텍처 맵`
4. `설계 철학`
5. `Clean·Hexagonal·DDD 평가`
6. `우선순위 발견`
7. `네이밍과 구조`
8. `이어갈 원칙`
9. `검증과 한계`

파일 규칙:

```text
wiki/services/{service_id}/analysis/architecture-analysis-{YYYY-MM-DD}-{short_sha}.md
wiki/services/{service_id}/analysis/assets/{note-stem}/{note-stem}.html
```

HTML은 Markdown과 별도로 다시 작성하지 않는다. frontmatter `resources`에 노트 기준 상대경로로 등록한다.

동일한 날짜·commit 파일이 이미 있으면 덮어쓰지 않는다. 사용자에게 기존 파일 갱신 또는 `-r2` revision 생성을 확인한다.

## 6. HTML 생성과 검증

```bash
python3 "$HARNESS/tools/render_architecture_report.py" "$NOTE" "$HTML"
python3 "$HARNESS/tools/lint_vault.py" --vault "$VAULT" --files "$NOTE"
```

확인 항목:

- renderer exit 0
- vault lint exit 0
- HTML에 외부 stylesheet/script dependency 없음
- Markdown의 필수 9개 섹션이 HTML 목차와 본문에 모두 존재
- P0/P1/P2/P3 표기가 시각적으로 구분됨
- 좁은 화면에서 표가 잘리지 않고 가로 스크롤됨
- print CSS가 포함됨

검증 후 문서를 자동으로 열지 않고 절대경로만 반환한다. Obsidian Git 같은 vault 자동화가 파일 open을 commit/push 신호로 사용할 수 있기 때문이다.

사용자가 명시적으로 열어 달라고 요청한 경우에만 vault 자동 commit/push 가능성을 먼저 알리고 `obsidian_open.sh`와 `open "$HTML"`을 실행한다.

## 7. 완료 응답

다음만 간결하게 보고한다.

- 한 문장 아키텍처 판정
- P0/P1 핵심 발견
- 실행·생략한 검증
- Markdown과 HTML 절대경로
- 대상 제품 저장소에 tracked 변경이 없다는 확인
- commit/push를 수행하지 않았다는 확인

ARGUMENTS: $ARGUMENTS
