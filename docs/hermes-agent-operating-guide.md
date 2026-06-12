# 에이전트 런타임 DEV2 운영 지침

이 문서는 Hermes Agent 같은 상시 에이전트를 개발 2팀 하네스와 로컬 Obsidian 운영 위키에 붙여 사용하는 기준이다. 목표는 코드 자동 작성이 아니라, 담당자 부재 상태의 레거시 서비스, SP, 아키텍처, 서비스 로직을 증거 기반 지식으로 복원하는 것이다.

Hermes는 이 구조의 첫 번째 후보 런타임이다. Claude Code와 Codex는 기존처럼 계속 별도 사용하고, 더 나은 에이전트가 나오면 같은 하네스 계약을 따르는 새 런타임으로 교체할 수 있어야 한다.

## 적용 목적

상시 에이전트는 다음 업무에 우선 적용한다.

| 우선순위 | 대상 | 기대 산출물 |
|---:|---|---|
| P0 | SP 중심 레거시 서비스 분석 | SP contract, caller map, table read/write, side effect |
| P0 | 담당자 없는 서비스 구조 복원 | architecture map, data ownership, unresolved evidence |
| P1 | 운영 문의와 장애 분석 | 영향 범위, 확인 순서, 검증 SQL 후보 |
| P1 | 현대화/DB 분리 준비 | readiness level, wrap/extract 후보, rollback 기준 |
| P2 | 티켓 prep와 PR 초안 | 5W1H, 영향 범위, 테스트 후보, 리뷰 체크리스트 |

에이전트가 만든 결과는 바로 팀 지식이 아니다. 팀 지식은 검증 가능한 근거와 사람 확인을 거쳐 vault 또는 team2 하네스의 정해진 위치로 승격된 산출물만 해당한다.

## 에이전트 중립 구조

DEV2의 핵심 기준은 특정 에이전트가 아니라 하네스 계약이다.

```text
사람 / YouTrack / 운영 요청
  ↓
DEV2 하네스 계약
  - 정책
  - evidence level
  - 저장 위치
  - 승인 게이트
  - 확인 패킷 형식
  ↓
에이전트 런타임
  - Claude Code
  - Codex
  - Hermes
  - 미래 에이전트
  ↓
draft 산출물
  ↓
사람 확인
  ↓
vault 또는 team2 하네스 승격
```

Claude Code와 Codex는 기존 개발·리뷰·수정 흐름에 그대로 둔다. Hermes는 상시 분석, 기억, 반복 탐색, 메시징/스케줄 실행 후보로 격리해서 쓴다. 어떤 런타임을 쓰더라도 아래 계약을 만족해야 DEV2 작업 결과로 인정한다.

| 계약 | 요구 사항 |
|---|---|
| 입력 계약 | team2 repo, vault, 서비스 repo를 명시된 권한으로 읽는다 |
| 출력 계약 | 분석 결과는 `draft`, `confirmed`, `needs-review`가 구분된 Markdown으로 남긴다 |
| 근거 계약 | source path, commit/hash 또는 추출 시점, caller, SP/table 근거를 남긴다 |
| 승인 계약 | YouTrack/KB/git/DB/배포 변경은 사람 승인 전 실행하지 않는다 |
| 교체 계약 | 에이전트 내부 memory/session/skill에만 있는 정보는 팀 지식으로 보지 않는다 |

## 런타임 교체 가능성 기준

새 에이전트를 도입하거나 Hermes를 교체할 때는 기능 목록보다 아래 기준을 먼저 본다.

| 기준 | 필요한 이유 |
|---|---|
| `AGENTS.md` 또는 동등한 project context 지원 | team2 하네스 규칙을 매번 재설명하지 않기 위함 |
| read-only mount 또는 workspace allowlist | 서비스 repo와 vault 훼손 방지 |
| output 전용 경로 지정 | draft 산출물과 원본 source를 분리 |
| credential allowlist | YouTrack, GitHub, DB, 배포 token의 기본 노출 방지 |
| command approval 또는 실행 금지 목록 | DB/SP 변경, 삭제, 배포 실행 차단 |
| 세션/메모리 export 가능성 | 교체 시 이전 런타임에 갇힌 지식 최소화 |
| Markdown 산출물 품질 | vault와 하네스에 승격하기 쉬운 형식 유지 |
| headless 또는 container 운영 | 상시 사용과 장애 복구 가능성 |

교체 절차는 다음 순서로 한다.

1. 새 에이전트를 별도 profile 또는 별도 container에 설치한다.
2. 같은 read-only source와 같은 output 경로 구조를 준다.
3. P0 서비스의 동일 SP 3개에서 5개를 분석시킨다.
4. Evidence Level, 확인 패킷, unresolved queue 품질을 비교한다.
5. 기존 Hermes memory/session에만 있는 지식은 vault draft로 내보낸다.
6. 새 에이전트가 기준을 통과하면 상시 runtime alias만 바꾼다.

에이전트를 바꾸더라도 vault 문서 구조, evidence level, SP contract 형식, 승인 게이트는 바꾸지 않는다.

## 저장소 경계

| 위치 | 용도 | 에이전트 사용 원칙 |
|---|---|---|
| 런타임 home | 에이전트 개인 세션, 메모리, 스킬, 설정 | 팀 canonical 지식으로 보지 않는다 |
| team2 repo | 정책, 절차, 템플릿, 서비스 카탈로그 | 운영 방식의 source of truth |
| Obsidian vault | 서비스 분석, 티켓 산출물, 도메인 지식, Querybook | 분석 결과의 기본 저장소 |
| 서비스 repo | 코드와 강결합된 사실, 빌드/실행/테스트 | 원본 근거로 읽고, 복제하지 않는다 |
| YouTrack KB | 전사/팀 공유가 필요한 공통 지식 | 사용자 승인 후에만 생성/수정 |

에이전트 내부 memory에는 “다음 탐색을 줄이는 개인 실행 힌트”만 저장한다. 서비스 로직, SP 계약, 데이터 소유권, 현대화 판단은 vault에 문서로 남겨야 한다.

## 운영 원칙

1. 요청은 YouTrack 5W1H 또는 명시된 분석 목표에서 시작한다.
2. 분석은 read-only를 기본값으로 한다.
3. DB/SP 변경, 프로덕션 배포, YouTrack/KB 변경, git push/PR/merge는 사람 승인 전에는 실행하지 않는다.
4. “전체 분석 완료”, “DB 분리 가능”, “SP 대체 가능”, “canonical” 같은 표현은 검증 기준을 만족하기 전에는 쓰지 않는다.
5. 모든 결론은 `confirmed`, `inferred`, `needs-review`로 나눈다.
6. 사용자에게 확인을 요청할 때는 원자료 덤프가 아니라 결정 가능한 요약과 근거 링크를 제공한다.

## 발견에서 확정까지의 지식 승격 흐름

```text
발견
  ↓
근거 수집
  ↓
계약 초안화
  ↓
모순/누락 점검
  ↓
확인 패킷 작성
  ↓
사람 확인
  ↓
vault canonical 후보 또는 하네스 정책 반영
  ↓
다음 분석의 시작 맥락으로 재사용
```

### 단계별 기준

| 단계 | 상태 | 의미 | 저장 |
|---|---|---|---|
| 1 | discovered | 이름, 호출 흔적, 파일 후보를 찾음 | 작업 메모 또는 draft |
| 2 | evidenced | source path, hash, caller, SP 원문 위치가 있음 | vault draft |
| 3 | analyzed | API/SP/Table read/write와 side effect를 연결함 | vault analysis |
| 4 | reviewed | 모순, source gap, owner gap, 검증 gap을 분리함 | unresolved queue 포함 |
| 5 | confirmed | 사람이 확인했거나 테스트/조회/리뷰로 검증됨 | relation_status confirmed |
| 6 | promoted | canonical 후보, decision, service index에 연결됨 | vault canonical 또는 team2 하네스 |

`confirmed`는 모델이 확신한다는 뜻이 아니다. 근거가 충분하고 사람이 확인 가능한 형태라는 뜻이다.

## Evidence Level

| Level | 이름 | 기준 | 사용 가능 범위 |
|---:|---|---|---|
| E0 | Candidate | 이름, 주석, 검색 결과만 있음 | 질문 후보 |
| E1 | Source Located | source path, 파일 hash, 추출 시점이 있음 | inventory |
| E2 | Contract Linked | caller, callee, SP, table read/write가 연결됨 | 영향 분석 초안 |
| E3 | Cross-Checked | 코드 경로와 DB script 또는 테스트가 서로 맞음 | reviewed analysis |
| E4 | Human Confirmed | 사용자가 확인했거나 PR/리뷰/운영 검증으로 인정됨 | confirmed 지식 |
| E5 | Migration Ready | shadow-read, reconciliation, rollback 기준이 있음 | 구현 착수 후보 |

현대화/DB 분리 의사결정에는 최소 E3가 필요하다. 구현 착수에는 E5 또는 별도 승인된 예외가 필요하다.

## 서비스 분석 산출물

서비스별 분석은 vault에 둔다.

```text
wiki/services/{service_id}/
  {service_id}-index.md
  analysis/
    {service_id}-inventory.md
    {service_id}-architecture-map.md
    {service_id}-sp-contracts.md
    {service_id}-domain-flows.md
    {service_id}-data-ownership.md
    {service_id}-unresolved-evidence.md
  decisions/
  proposals/
  processes/
```

원본 코드, SQL script, schema 파일은 vault에 복제하지 않는다. vault에는 source path, commit/hash, 해석, 판단, 검증 방법만 남긴다.

## SP Contract 최소 필드

SP 하나를 분석할 때 에이전트는 아래 항목을 채워야 한다.

| 항목 | 내용 |
|---|---|
| SP 식별자 | DB, schema, SP name |
| 원본 근거 | repo, path, hash, 추출 시점 |
| 호출자 | API, batch, service method, job, 수동 실행 여부 |
| 입력 계약 | parameter, nullable, 기본값, 의미 |
| 출력 계약 | result set, return code, error code |
| read table | 조회 table, join, NOLOCK, cross DB |
| write table | insert/update/delete/merge, 원장 여부 |
| side effect | mail, queue, file, cache, search index, statistics |
| 트랜잭션 | explicit transaction, retry, partial success |
| 운영 위험 | lock, batch lag, amount mismatch, stale data |
| 소유권 후보 | write owner, read consumer, shared owner |
| 검증 방법 | 테스트, read-only SQL, reconciliation query |
| 미확정 항목 | source gap, schedule gap, owner gap |
| review_state | `needs-review`, `reviewed`, `confirmed` |

SP contract 문서에서 빠진 항목은 “없음”으로 쓰지 않는다. 확인하지 못했으면 `unknown` 또는 `needs-review`로 남긴다.

## 사용자 확인 패킷

사용자에게 최종 확인을 요청할 때 에이전트는 원자료를 길게 붙이지 않는다. 아래 형태로 압축한다.

```markdown
## 확인 요청

### 확정해도 되는 내용
- [E3] `{SP_NAME}`은 주문 생성 시 `{table}`에 write한다.
  근거: `{source path}`, caller `{method}`, 검증 `{query/test}`

### 유용하지만 아직 추론인 내용
- [E2] 정산 집계는 주문 시점 스냅샷을 기준으로 보인다.
  부족한 근거: batch schedule 확인 필요

### 확인이 필요한 질문
1. `{SP_NAME}`의 실제 운영 실행 주체가 API인지 batch인지 확인 필요
2. `{table}`을 원장으로 봐도 되는지 확인 필요

### 결정 후보
- 지금은 read path wrap만 후보로 두고, write path extract는 보류한다.
```

확인 패킷은 다음 원칙을 따른다.

- 한 번에 확인할 질문은 1개에서 3개로 제한한다.
- 각 질문은 결정 결과가 바뀌는 항목만 묻는다.
- 파일 목록, grep 결과, 콜그래프 전체는 부록으로 분리한다.
- 확정 가능한 내용과 미확정 내용을 한 문장 안에 섞지 않는다.

## 에이전트 작업 모드

### 1. Discovery 모드

목표는 전체 이해가 아니라 분석 seed를 만드는 것이다.

사용 시점:
- 서비스 담당자가 없고 구조를 모를 때
- SP, table, batch, API 목록이 흩어져 있을 때
- Graphify 또는 기존 위키가 stale일 때

출력:
- inventory
- source gap
- P0 분석 후보
- 다음에 검증할 질문

### 2. Contract 모드

목표는 API/SP/Table의 계약을 연결하는 것이다.

사용 시점:
- 특정 티켓 또는 운영 문의의 영향 범위를 봐야 할 때
- SP를 감싸거나 대체할 수 있는지 판단해야 할 때

출력:
- SP contract
- caller map
- data ownership 후보
- read/write 분리 후보

### 3. Review 모드

목표는 에이전트가 만든 분석을 의심하는 것이다.

확인 항목:
- source path가 실제 존재하는가
- caller와 SP parameter가 맞는가
- read/write table이 누락되지 않았는가
- batch, scheduler, 수동 실행 경로가 빠지지 않았는가
- 추론을 confirmed로 잘못 올리지 않았는가

### 4. Promotion 모드

목표는 검증된 분석만 팀 지식으로 승격하는 것이다.

승격 대상:
- vault `analysis`의 `status: draft`에서 `status: canonical` 후보로 이동
- vault `decision` 문서 생성
- team2 `catalog/{service}.yaml`의 서비스 경계 보강
- team2 정책/템플릿 개선 제안

실제 KB 변경, 커밋, push, PR 생성은 사용자 승인 후 별도 실행한다.

## 권장 프롬프트

### 서비스 최초 분석

```text
{service_id} 서비스를 Discovery 모드로 분석해줘.
목표는 전체 분석 완료가 아니라 P0 분석 seed 작성이야.
API, batch, SP, table 후보를 찾고 E0/E1로 분류해.
확정 표현은 쓰지 말고 source path와 미확정 queue를 남겨.
```

### SP 계약 분석

```text
{SP_NAME}을 Contract 모드로 분석해줘.
caller, parameter, read/write table, side effect, failure mode를 분리하고
각 항목에 Evidence Level을 붙여.
사용자 확인 패킷은 3개 질문 이하로 압축해.
```

### 분석 검토

```text
이 분석을 Review 모드로 검토해줘.
confirmed로 올리면 안 되는 추론, source gap, owner gap, batch schedule gap을 찾아.
최종 출력은 확정 가능 / 추론 / 확인 필요 / 보류로 나눠줘.
```

### 위키 승격

```text
검증된 항목만 Promotion 모드로 정리해줘.
vault에 남길 analysis/decision 후보와 team2 하네스에 반영할 정책/카탈로그 후보를 분리해.
커밋, YouTrack, KB 변경은 실행하지 말고 초안만 작성해.
```

## Docker 사용 판단 기준

Hermes를 상시로 쓸 때는 Hermes 자체를 Docker에서 실행하는 구성이 기본 후보가 된다. 이때 컨테이너는 에이전트 런타임의 격리 경계이고, team2 하네스와 vault는 바깥의 교체 불가능한 기준으로 남긴다.

| 방식 | 의미 | DEV2 권장도 |
|---|---|---|
| Hermes 자체를 Docker에서 실행 | Hermes 프로세스, config, session, gateway가 컨테이너 안에서 실행됨 | 상시 사용 기본 후보 |
| Docker terminal backend | Hermes는 host에서 실행하고, terminal/file/code tool은 Docker sandbox에서 실행됨 | host 설치형 pilot 때만 검토 |
| Hermes Docker + Docker terminal backend | 컨테이너 안 Hermes가 다시 Docker backend를 호출 | 기본 금지 |

상시 운영에서는 Hermes 자체 Docker 컨테이너 안의 `local` 실행 환경을 사용하고, host 디렉터리는 read-only 또는 output 전용으로 mount한다. Docker socket은 mount하지 않는다.

상시 Hermes 컨테이너 권장 방향:

```yaml
services:
  hermes-team2:
    image: nousresearch/hermes-agent:latest
    container_name: hermes-team2
    restart: unless-stopped
    command: gateway run
    volumes:
      - "/Users/jm/.hermes-team2:/opt/data"
      - "/Users/jm/Documents/workspace/team2:/workspace/team2:ro"
      - "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2:/workspace/team2-vault:ro"
      - "/Users/jm/.hermes-team2-output:/workspace/output:rw"
```

CLI로만 시작할 때는 같은 volume 구조로 interactive container를 실행한다.

```bash
docker run -it --rm \
  -v "/Users/jm/.hermes-team2:/opt/data" \
  -v "/Users/jm/Documents/workspace/team2:/workspace/team2:ro" \
  -v "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2:/workspace/team2-vault:ro" \
  -v "/Users/jm/.hermes-team2-output:/workspace/output:rw" \
  nousresearch/hermes-agent
```

host 설치형 Hermes를 pilot으로 쓸 때만 아래처럼 Docker terminal backend를 검토한다.

```yaml
approvals:
  mode: manual
  cron_mode: deny

terminal:
  backend: docker
  docker_image: "nikolaik/python-nodejs:python3.11-nodejs20"
  docker_mount_cwd_to_workspace: false
  docker_run_as_host_user: true
  docker_forward_env: []
  env_passthrough: []
  docker_volumes:
    - "/Users/jm/Documents/workspace/team2:/workspace/team2:ro"
    - "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2:/workspace/team2-vault:ro"
    - "/Users/jm/.hermes/team2-output:/workspace/output:rw"
```

서비스 repo는 전체 workspace를 한 번에 열지 말고, 분석 대상 서비스만 read-only로 mount한다.

```yaml
    - "/Users/jm/Documents/workspace/{service-repo}:/workspace/repos/{service_id}:ro"
```

금지:

- `--yolo` 사용
- `approvals.mode: off`
- Docker socket mount
- 운영 DB credential 전달
- `YOUTRACK_TOKEN`, `GITHUB_TOKEN`, 배포 token의 기본 forwarding
- messaging gateway 공개 노출
- dashboard insecure 모드
- service repo와 vault를 같은 쓰기 mount로 열기

Claude Code와 Codex는 이 Docker 구성에 묶지 않는다. 기존처럼 host 또는 각 도구의 표준 실행 방식으로 쓰고, 산출물이 DEV2 하네스 계약을 만족하는지만 확인한다.

## 도입 단계

### Phase 0: 로컬 read-only pilot

기간: 1주

대상:
- P0 서비스 1개
- SP 5개에서 10개
- 기존 위키/Graphify 산출물과 비교 가능한 범위

성공 기준:
- SP contract 초안 5개 이상
- source gap과 owner gap이 명시됨
- 사용자 확인 패킷이 원자료보다 짧고 결정 가능함
- vault에 `draft` 분석 문서가 남음
- 민감정보와 local path가 YouTrack/KB로 유출되지 않음

### Phase 1: 서비스별 분석 팩

기간: 2주에서 4주

대상:
- P0 서비스 1개 또는 2개
- architecture map
- data ownership
- unresolved evidence

성공 기준:
- 최소 L3 ownership 분석
- 운영 문의 또는 티켓 prep에서 재사용
- 같은 SP/테이블 재탐색 시간이 감소

### Phase 2: 하네스 강화

기간: pilot 이후

대상:
- 반복되는 실수
- 빠진 템플릿
- 부족한 서비스 catalog
- 위험 SP guardrail

성공 기준:
- 특정 에이전트 없이도 사람이 같은 분석 기준을 따라갈 수 있음
- 새 티켓 착수 시 읽을 문서가 명확함
- 확인 질문 수가 줄고, 질문 품질이 좋아짐

## 완료 기준

에이전트 분석을 완료로 보려면 아래를 만족해야 한다.

- 분석 범위가 명시되어 있다.
- 각 결론에 Evidence Level이 있다.
- confirmed와 inferred가 분리되어 있다.
- source path, hash 또는 추출 시점이 있다.
- SP contract에서 read/write와 side effect가 분리되어 있다.
- owner gap, source gap, schedule gap이 unresolved queue에 남아 있다.
- 사용자 확인 패킷이 있다.
- vault 문서는 `draft`로 저장되고, 사람 확인 후에만 `confirmed` 또는 `canonical` 후보로 승격된다.

## 관련 문서

- [하네스 운영 가이드](./harness-guide.md)
- [LLM 위키 운영 가이드](./llm-wiki-operating-guide.md)
- [레거시 현대화와 DB 분리 분석 기준](./legacy-modernization-db-separation-analysis-guide.md)
- [운영 위키 문서 언어와 제목 정책](../policies/wiki-document-language-and-title-policy.md)
- [AI 사용 정책](../policies/ai-usage-policy.md)
- Hermes 공식 문서: [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration), [Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker), [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security), [Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files), [Persistent Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
