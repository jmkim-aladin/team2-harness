# Datadog API 정책

Datadog API 자격증명의 저장·사용·금지 규칙. 비민감 접근 정보(site, endpoint, 자격증명 참조명)는 [`catalog/datadog.yaml`](../catalog/datadog.yaml), Keychain 사용 표준은 [local-credentials-policy.md](./local-credentials-policy.md), 공통 취급 원칙은 [security-policy.md](./security-policy.md) §취급 공통 원칙을 따른다.

## 민감/비민감 분리

| 구분 | 항목 | 저장 위치 |
|------|------|-----------|
| 비민감 | site, api_base, org 이름, **API key의 Key ID(UUID)**, Keychain 참조명, 권장 scope, dashboard ID, service tag | 하네스 repo (`catalog/datadog.yaml`, `catalog/datadog-idc-db-monitoring.yaml`) |
| 민감 | API key 값, Application key 값 | macOS Keychain **only** |

dashboard ID, service tag, Key ID는 그 자체로 접근 권한을 주지 않으므로 비민감으로 본다. Key ID는 회전·revoke 시 대상 키를 특정하는 데 쓴다. 키 값은 어떤 경우에도 repo·vault·티켓·Slack·PR에 남기지 않는다.

## 키 종류

- **API key** (`DD-API-KEY`) — org 단위. Datadog UI에서 Key ID(UUID) + 키 값 쌍으로 보여준다.
- **Application key** (`DD-APPLICATION-KEY`) — 발급한 사람의 권한을 그대로 상속한다.

**API key 단독으로 할 수 있는 일은 제한적이다.** intake(메트릭/로그/이벤트 전송)와 `/api/v1/validate`만 가능하다. 대시보드 조회, metrics query, logs search 등 읽기 API는 두 헤더를 모두 요구하므로 Application key가 반드시 필요하다.

Application key는 반드시 **scope를 명시해 발급**한다. scope 없이 발급하면 발급자 권한 전체를 가진 키가 된다. 부여할 scope 목록은 `catalog/datadog.yaml`의 `scopes`.

팀 용도는 대시보드 **조회 + 생성/수정**까지다. 따라서 `dashboards_write`를 부여한다. Datadog은 대시보드 생성·수정·삭제를 `dashboards_write` 하나로 묶어 제공하므로 scope로 삭제만 떼어낼 수 없다 — 삭제는 아래 금지 규칙으로 막는다.

`monitors_write`는 부여하지 않는다. 모니터/알럿 변경은 장애 대응 경로에 직접 영향을 주므로 Datadog UI에서 사람이 수행한다.

## 등록

키 등록은 **본인이 직접** 한다 (AI에게 `add-generic-password`를 시키지 않는다).

```bash
security add-generic-password -s "team2-datadog-api-key"  -a "{owner 계정}" -w
security add-generic-password -s "team2-datadog-app-key"  -a "{owner 계정}" -w
```

`-w`를 값 없이 두면 프롬프트로 입력받아 셸 history에 남지 않는다. 갱신은 `-U` 추가.

주의: AI 세션의 `!` 명령 패스스루로 실행하면 대화형 프롬프트가 입력을 받지 못해 **빈 값이 저장된다** (에러 없이 통과). 등록은 별도 터미널에서 하고, 아래로 저장 여부를 확인한다 (근거: AI `!` 패스스루 빈 값 저장 사례).

```bash
K=$(security find-generic-password -s "team2-datadog-api-key" -a "{owner 계정}" -w); echo "${#K}"; unset K
```

API key는 32자 hex. `0`이면 빈 값이므로 `-U`로 재등록한다.

## 조회·호출

```bash
DD_API_KEY=$(security find-generic-password -s "team2-datadog-api-key" -a "{owner 계정}" -w)
DD_APP_KEY=$(security find-generic-password -s "team2-datadog-app-key" -a "{owner 계정}" -w)

curl -sS "https://api.datadoghq.com/api/v1/validate" \
  -H "DD-API-KEY: $DD_API_KEY"

curl -sS "https://api.datadoghq.com/api/v1/dashboard/we5-wce-ez6" \
  -H "DD-API-KEY: $DD_API_KEY" -H "DD-APPLICATION-KEY: $DD_APP_KEY"

unset DD_API_KEY DD_APP_KEY
```

- `-H` 헤더로만 전달한다. URL query string에 키를 붙이면 프록시·서버 로그에 남는다.
- 사용 후 즉시 `unset`.
- `curl -v`, `set -x`는 헤더를 그대로 출력하므로 키가 로드된 셸에서 쓰지 않는다.

## 금지

- 키 값을 `catalog/datadog.yaml` 등 repo 파일, vault 노트, YouTrack 티켓·KB, Slack, PR 본문에 기재
- `.env`·평문 파일·MCP 서버 설정에 키 하드코딩
- **API로 대시보드 삭제** (`DELETE /api/v1/dashboard/{id}`) — key scope로는 막을 수 없으므로 규칙으로 금지. 삭제는 Datadog UI에서 사람이 수행
- `monitors_write` 등 대시보드 외 write scope 부여
- 기존 팀 대시보드(`catalog/datadog-idc-db-monitoring.yaml` 등록분) 덮어쓰기 — 신규 생성은 새 대시보드로, 기존 대시보드 수정은 사용자 확인 후에만
- 팀원 간 키 공유 — 각자 본인 키를 발급해 본인 Keychain에 등록
- `curl` 응답 원문을 그대로 로그/리뷰 산출물에 남기기 (host·계정 정보가 섞일 수 있음)

## AI 도구 사용 시

- 읽기 호출(`GET` 계열: validate, dashboard/monitor 조회, metrics/logs 쿼리)은 사전 동의로 본다. 매 호출 확인 없이 실행 가능.
- 대시보드 **신규 생성**(`POST /api/v1/dashboard`)은 위젯 구성 요약을 먼저 제시하고 사용자 확인 후 호출한다. 생성 후 dashboard ID와 URL을 보고한다.
- 기존 대시보드 **수정**(`PUT /api/v1/dashboard/{id}`)은 대상 ID·변경 위젯·되돌리는 방법을 제시하고 확인 후 호출한다. `PUT`은 전체 교체이므로 먼저 `GET`으로 현재 정의를 받아 병합한다.
- `DELETE`는 호출하지 않는다.
- 그 밖의 쓰기 호출은 **매번 사용자 확인 필수**. 요청 body와 영향 범위를 먼저 제시한다.
- 응답에서 키가 포함될 수 있는 필드(`api_key`, `application_key` 목록 API 등)는 조회하지 않는다.
- 키를 조회했으면 그 값을 사용자 응답·노트·커밋에 인용하지 않는다.

## 회전

- 키 노출 의심 시 Datadog UI에서 즉시 revoke → 신규 발급 → Keychain `-U` 갱신.
- 담당자 퇴사/이동 시 해당 Application key revoke (org API key는 별도 판단).
