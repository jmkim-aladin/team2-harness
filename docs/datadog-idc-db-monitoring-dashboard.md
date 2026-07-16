# DB 이관 Datadog 대시보드 구성

## 목적

IDC DB 이전 기간에 개발2팀 서비스의 장애 징후를 한 화면에서 보고, 서비스별로 원인 확인에 필요한 지표를 바로 볼 수 있게 한다.

서비스 매핑의 source of truth는 [`catalog/datadog-idc-db-monitoring.yaml`](../catalog/datadog-idc-db-monitoring.yaml)이다. Datadog `service` tag 값과 dashboard slug는 모두 lowercase로 관리한다.

## 대시보드 구성도

```text
dev2-idc-db-migration-overview
├── dev2-idc-db-migration-naru
│   ├── naru-account-api
│   └── naru-sso-api
├── dev2-idc-db-migration-max
│   ├── maxapi
│   ├── max-front
│   ├── maxims-front
│   └── max-search
├── dev2-idc-db-migration-tobe
│   └── tobe-web
├── dev2-idc-db-migration-blog
│   └── blog-web
└── dev2-idc-db-migration-bazaar
    └── bazaar-batch-api
```

## 전체 현황 대시보드

대시보드 slug: `dev2-idc-db-migration-overview`

| 영역 | 위젯 | 기준 |
|---|---|---|
| 개요 | 전체 설명, 서비스별 상세 대시보드 링크 | 빈 그래프는 tag/instrumentation 공백 후보 |
| 요청량 | APM `http`, `web`, `servlet`, `aspnet` request hits | 서비스별 traffic 변화 |
| 오류 | APM request errors, HTTP status errors | 이전 전후 오류 급증 |
| 지연 | p95 request latency | DB 이전 영향 전파 |
| DB/cache | `sqlserver`, `postgresql`, `redis` errors | DB/캐시 의존 영향 |
| 서비스 그룹 | naru, max, tobe, blog, bazaar별 group | 한 화면에서 서비스별 이상 징후 비교 |

## 서비스별 대시보드

서비스 그룹 안에 Datadog `service` tag가 여러 개인 경우, 전체 대시보드는 그룹 합산을 유지하고 상세 대시보드에는 `service detail: {service}` 그룹을 둔다. 원인 파악은 상세 대시보드의 개별 service tag 섹션에서 먼저 확인한다.

### naru

대시보드 slug: `dev2-idc-db-migration-naru`

대상 서비스: `naru-account-api`, `naru-sso-api`

| 영역 | 위젯 |
|---|---|
| group summary | naru 전체 5xx, 4xx noise, 요청량, 지연 |
| service detail: naru-account-api | account-api 개별 요청/5xx/4xx/resource/DB-cache |
| service detail: naru-sso-api | sso-api 개별 요청/5xx/4xx/resource/DB-cache |
| APM 요청/오류 | total requests, total errors, requests/errors by service, HTTP status hits/errors |
| latency / endpoint | p95, p99, apdex, top resources by requests/errors |
| DB/cache 영향 | sqlserver/postgresql/redis hits, errors, p95 latency, resource별 오류 |
| runtime / infra | kubernetes, ecs, iis, host cpu/memory 후보 지표 |
| drill-down | Logs Explorer/Trace Explorer query |

### max

대시보드 slug: `dev2-idc-db-migration-max`

대상 서비스: `maxapi`, `max-front`, `maxims-front`, `max-search`

| 영역 | 위젯 |
|---|---|
| group summary | max 전체 5xx, 4xx noise, 요청량, 지연 |
| service detail: maxapi | `trace.aspnet.request` 기준 maxapi 개별 요청/5xx/4xx/resource |
| service detail: max-front | max-front 개별 요청/5xx/4xx/resource/DB-cache |
| service detail: maxims-front | maxims-front 개별 요청/5xx/4xx/resource/DB-cache |
| service detail: max-search | max-search 개별 요청/5xx/4xx/resource/DB-cache |
| application errors | 5xx app errors, 5xx by service/status/resource |
| 4xx noise | 403/404 등 4xx access/resource noise를 app error에서 제외하고 별도 표시 |
| latency / endpoint | p95, p99, apdex, top resources by requests/errors |
| DB/cache 영향 | sqlserver/postgresql/redis hits, errors, p95 latency, resource별 오류 |
| runtime / infra | kubernetes, ecs, iis, host cpu/memory 후보 지표 |
| drill-down | Logs Explorer/Trace Explorer query |

max는 Datadog APM error metric에 403/404가 함께 잡히므로, 기본 오류 수치는 `http.status_code:5*`만 사용한다. 4xx는 접근 거부/미존재 리소스 노이즈 영역으로 분리한다.
maxapi는 `trace.aspnet.request`만 실질 수집되고 `trace.http.request`, `trace.web.request`, `trace.sqlserver.query`, `trace.redis.command`는 현재 `maxapi` service tag로 거의 잡히지 않는다.

### tobe

대시보드 slug: `dev2-idc-db-migration-tobe`

대상 서비스: `tobe-web`

| 영역 | 위젯 |
|---|---|
| application errors | 5xx app error candidates, 5xx by service/status/resource |
| business/auth noise | `Aladin.Tobe.Core.TobeException: 로그인이 필요합니다.` 로그 확인 |
| 4xx noise | 403/404 등 4xx access/resource noise를 app error에서 제외하고 별도 표시 |
| latency / endpoint | p95, p99, apdex, top resources by requests/errors |
| DB/cache 영향 | sqlserver/postgresql/redis hits, errors, p95 latency, resource별 오류 |
| drill-down | Logs Explorer/Trace Explorer query |

투비는 `Aladin.Tobe.Core.TobeException: 로그인이 필요합니다.`가 HTTP 500으로 떨어질 수 있으나 실제 장애가 아닌 로그인 필요 business/auth noise로 본다. Datadog APM metric만으로 message 제외가 어려우므로, 투비 대시보드는 5xx를 application error candidate로 표시하고 해당 문자열 로그를 별도 noise 영역에서 확인한다.

### blog

대시보드 slug: `dev2-idc-db-migration-blog`

대상 서비스: `blog-web`

| 영역 | 위젯 |
|---|---|
| aspnet request overview | requests, 5xx, 4xx, resource traffic, p95/p99 |
| application errors | 5xx by resource/status |
| traffic shape | top resources, apdex, blocked-resource traffic |
| DB/cache instrumentation status | `blog-web` tag로 DB/cache span이 현재 미수집임을 표시 |
| drill-down | Logs Explorer/Trace Explorer query |

blog는 `trace.aspnet.request` 중심으로 수집된다. `trace.http.request`, `trace.web.request`, `trace.sqlserver.query`, `trace.redis.command`는 현재 `blog-web` service tag로 거의 잡히지 않으므로 상세 대시보드는 ASP.NET request 기준으로 본다.

### bazaar

대시보드 slug: `dev2-idc-db-migration-bazaar`

대상 서비스: `bazaar-batch-api`

| 영역 | 위젯 |
|---|---|
| APM 요청/오류 | total requests, total errors, requests/errors by service, HTTP status hits/errors |
| latency / endpoint | p95, p99, apdex, top resources by requests/errors |
| DB/cache 영향 | sqlserver/postgresql/redis hits, errors, p95 latency, resource별 오류 |
| runtime / infra | kubernetes, ecs, iis, host cpu/memory 후보 지표 |
| drill-down | Logs Explorer/Trace Explorer query |

## Datadog 태그 기준

| 태그 | 값 |
|---|---|
| `team` | `dev2` |
| `event` | `idc-db-migration` |
| `service` | `catalog/datadog-idc-db-monitoring.yaml`의 `datadog_services` 값 |
| `env` | Datadog 기존 환경 tag를 따른다 |

## 운영 기준

- 전체 대시보드는 장애 징후 감지용으로 쓰고, 상세 원인 확인은 서비스별 대시보드에서 한다.
- DB 이전 전 baseline 기간과 이전 중 기간을 같은 time range preset으로 비교한다.
- alert는 대시보드 구성 후 별도 검토한다. 현재 문서는 dashboard 구성 기준만 정의한다.
- Datadog service tag를 변경할 때는 `catalog/datadog-idc-db-monitoring.yaml`을 먼저 갱신한다.
