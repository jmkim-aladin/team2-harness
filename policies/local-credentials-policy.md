# 로컬 자격증명 정책 (macOS Keychain)

로컬 개발 환경에서 개발(dev)/스테이징(staging) DB·외부 API 자격증명을 다룰 때의 규칙. 운영 자격증명과 런타임 시크릿 주입은 [aws-secrets-convention.md](./aws-secrets-convention.md), 일반 보안 규칙은 [security-policy.md](./security-policy.md)를 따른다.

## 범위

공통 취급 원칙: [security-policy.md](./security-policy.md) §취급 공통 원칙.

- 대상: 팀원 본인 개발 머신에 한정.
- 저장 매체: **OS 네이티브 금고** — macOS는 Keychain(login), **Windows는 Credential Manager**(DPAPI, 사용자별 암호화). `~/.env`, 평문 파일, 프로젝트 디렉터리, vault, 하네스, **`~/.claude/settings.json` env** 저장 금지 (근거: 2026-08-08 — settings.json에 YOUTRACK_TOKEN 평문 발견, Keychain 이관)
- 접근 인터페이스는 OS 공통으로 **`python3 tools/cred.py`** 하나 — `get <name>`(stdout) / `set <name>`(프롬프트, 인자 금지 — 셸 히스토리 방지) / `check`(manifest 선언분 존재 검사, 값 미출력). macOS는 `security` CLI 폴백이라 의존성 0, Windows는 `pip install keyring` 1회
- 필요한 자격증명 **이름 목록**(값 아님)은 [harness.manifest.json](../harness.manifest.json) `credentials`가 SoT — `setup_harness.py --check`가 누락을 검출하고 등록 명령을 안내한다
- 유출 감시: `python3 tools/secret_scan.py` — repo+vault 패턴 스캔, `/ad:harness-optimize 스택` 모드에 포함. 발견 시 제거 + **해당 자격증명 재발급**이 원칙 (한 번 파일에 닿은 값은 오염으로 간주)
- 보관 가능: dev/staging DB 비밀번호, dev 외부 API 키, 로컬 도구 토큰(YouTrack, GitHub, 사내 시스템 등).
- 보관 범위 밖: 운영 API 시크릿, 타인 계정 자격증명, 결제·개인정보 관련 운영 자격증명. 운영 DB의 개인 키체인 등록은 아래 §운영 DB 키체인 등록 준비의 명시된 대상에 한해 준비하며, 실제 접근은 운영 DB 접근 정책의 개통 조건을 따른다.

## 네이밍 컨벤션

Keychain `service` 필드는 AWS Secrets Manager 컨벤션과 정렬한다.

```
sm-{서비스}-{모듈}-{환경}-{리소스}        # AWS SM과 동일 이름 → 매핑 용이
```

| 예시 | 용도 |
|------|------|
| `sm-max-admin-dev-database-read` | max admin dev 읽기 DB |
| `sm-naru-sso-dev-database-write` | naru sso dev DB |
| `team2-youtrack-token` | YouTrack PAT (서비스 무관 도구) |
| `team2-github-token` | GitHub PAT |
| `fortify-ssc-analysis-upload-token` | Fortify SSC FPR 등록용 `AnalysisUploadToken`의 encoded token — [정적 점검 런북](../docs/static-scan-runbook.md) |
| `team2-datadog-api-key` / `team2-datadog-app-key` | Datadog API/Application key — [datadog-api-policy.md](./datadog-api-policy.md) |

`account` 필드는 DB 사용자명 또는 본인 사번/이메일을 사용한다 (`jmkim@aladin.co.kr` 등).

## 저장

GUI(키체인 접근.app)로 직접 등록하거나 CLI로:

```bash
security add-generic-password \
  -s "sm-max-admin-dev-database-read" \
  -a "$(whoami)" \
  -w '비밀번호'        # -w 뒤 공백 후 입력하면 history에 안 남는 셸도 있음. 빈 -w로 두고 프롬프트 입력.
```

업데이트는 `-U` 플래그. **단일 따옴표로 감싸 셸 history 노출을 줄인다**. `set -o history` 비활성 셸에서만 직접 인자 입력.

## 조회

> macOS 내부 구현·직접 조회 예시 — 표준 인터페이스는 §범위의 `python3 tools/cred.py`이고, Windows는 cred.py만 가능하다.

```bash
# 비밀번호만 출력 (스크립트 친화)
security find-generic-password -s "sm-max-admin-dev-database-read" -a "$(whoami)" -w

# 메타데이터 + 비밀번호 (확인용)
security find-generic-password -s "sm-max-admin-dev-database-read" -a "$(whoami)" -g
```

CLI 호출 시 macOS가 키체인 잠금 해제 프롬프트를 띄울 수 있다 — 자동 승인하지 말고 본인이 입력한다. 항상 허용(Always Allow)은 신중히.

### 권장 사용 패턴

```bash
# SQL 검증 (mssql-cli 예시)
PW=$(security find-generic-password -s "sm-max-admin-dev-database-read" -a "$(whoami)" -w)
mssql-cli -S dev-host -d webcatalog -U readonly_user -P "$PW" -Q "SELECT TOP 10 ..."
unset PW                              # 사용 후 즉시 해제
```

```bash
# SQL 검증 (sqlcmd / go-sqlcmd 예시) — 비밀번호는 -P 대신 SQLCMDPASSWORD env로 전달
PW=$(security find-generic-password -s "sm-max-admin-dev-database-read" -a "$(whoami)" -w)
SQLCMDPASSWORD="$PW" sqlcmd -S dev-host -d webcatalog -U readonly_user -Q "SELECT TOP 10 ..."
unset PW
```

- 환경변수에 두고 즉시 `unset`. 셸 history에 평문이 남지 않도록 한다.
- `sqlcmd`는 `-P <암호>`로 넘기면 `ps`에 평문이 노출된다. `SQLCMDPASSWORD` env로 전달해 프로세스 인자 노출을 막는다.
- `tee`, `>` 리다이렉트, 임시 파일 저장 금지.
- 결과 화면에 비밀번호가 echo되지 않도록 `-w`만 캡처해 변수로 받는다.

여러 dev DB를 자주 쓰면 위 패턴을 셸 함수로 감싼다. account 필드는 등록한 값(DB 사용자명 또는 사번/이메일)과 일치시킨다 — `$(whoami)`와 다를 수 있다. 자격증명·host는 함수에 박지 말고 Keychain 조회 + target→host 매핑만 둔다.

## 등록된 dev DB 매핑 (target → host)

각자 머신 기준. 비밀번호는 아래 keychain `service`에서 조회, host는 이 표에서 찾는다. 개발 데이터 변경 범위는 아래 §개발 DB 데이터 입력·수정·삭제를 따른다. `{계정}`은 각자 등록값(DB 사용자명 또는 사번)으로 치환한다.

| keychain service | account | host | 비고 |
|------------------|---------|------|------|
| `cool-dev` | `{계정}` | `rds-cluster-cool-dev.cleuiesc8bqi.ap-northeast-2.rds.amazonaws.com` | 공유 MSSQL dev. DB: `WebCatalog`, `ToBe`, `Community`, `WebLog`, `WebMarket` (tobe/max/shopping/blog 공유) |
| `lego-dev` | `{계정}` | (Lego 링크드 서버 dev — `Lego.WebStat` 등) | 통계/로그 계열. host는 본인 등록값 |
| `aasm-dev` | `{계정}` | rds-52-web-common-contents-dev.cluster-cv2ku20yeh9n.ap-northeast-2.rds.amazonaws.com | aasm postgresql dev DB |

클라이언트는 go-`sqlcmd`(`/opt/homebrew/bin/sqlcmd`). tools18 미설치 시 `-C`(서버 인증서 신뢰) 필요.

```bash
PW=$(security find-generic-password -s "cool-dev" -a "{계정}" -w)   # {계정} = 각자 등록값
SQLCMDPASSWORD="$PW" sqlcmd -S "rds-cluster-cool-dev.cleuiesc8bqi.ap-northeast-2.rds.amazonaws.com" \
  -U "{계정}" -C -d WebCatalog -h -1 -W -Q "SELECT TOP 10 ..."
unset PW
```

> 신규 항목은 `sm-{서비스}-{모듈}-{환경}-{리소스}` 컨벤션 권장. `cool-dev`/`lego-dev`는 기존 단축 등록명(레거시) — 이 표로 매핑 보존.

## 운영 DB 키체인 등록 준비

2026-10-14 사용자 요청에 따라 `cool-prod`·`lego-prod`의 비밀번호와 접속 정보를 개인 키체인에 등록할 양식을 준비한다. 비밀번호는 기존 service에, 주소·포트·계정은 별도 profile service의 JSON에 보관한다. 2026-10-15 사용자 요청으로 JSON을 `host`·`port`·`account` 세 필드로 단순화했다. profile 항목의 키체인 account는 `profile`이다. 서버 역할은 개통 검증 후 보호된 실행기 설정에서 관리한다. TLS 암호화는 필수 적용하며, 2026-10-15 사용자 승인에 따라 `-N true -C`로 서버 인증서를 신뢰하고 인증서 검증은 생략한다. 실제 접속 정보는 하네스·위키에 기록하지 않는다.

| target / 비밀번호 service | 접속 정보 service | 상태 |
|---|---|---|
| `cool-prod` | `cool-prod-profile` | 미개통 |
| `lego-prod` | `lego-prod-profile` | 비밀번호 키체인 저장 완료(사용자 확인), 미개통 |

복사용 빈 JSON 양식은 사용자 지정 위치인 `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/projects/production-db-access/production-db-access.md`에 둔다. 2026-10-15 사용자 요청에 따라 위키의 허용 DB 목록은 제거하고 등록 양식과 사용 안내만 유지한다.

키체인 등록은 운영 개통이나 SQL 실행 승인을 뜻하지 않는다. 2026-10-15 사용자 선택에 따라 현재 macOS 계정의 로그인 키체인을 전용 실행기가 읽는다. [운영 DB 접근 정책](./production-db-access-policy.md)의 매 실행 승인을 적용하며, JSON 로더와 네이티브 키체인 helper 코드는 준비했다. 프로파일은 준비 시 읽고 비밀번호는 승인 소비 후 연결 직전에만 읽는다. 같은 UID의 직접 접근을 OS 권한으로 격리하는 구성은 아니다. 후속 진행 요청으로 초기화·실행기 시작과 lego 프로파일 읽기를 확인했다. 운영 연결은 SQL 전문 승인 전까지 보류한다. 이유: 저장 양식과 실제 접근 권한을 구분하고, SQL 전문과 실제 대상에 대한 매 실행 사용자 승인을 유지하기 위해서다.

## 금지

- 비밀번호를 위키/하네스/Slack/티켓에 평문 붙여넣기 (요청 시 마스킹 후 공유)
- `~/.netrc`, `~/.my.cnf`, `~/.pgpass` 등 평문 파일에 운영 자격증명 저장 (dev는 부득이할 경우 `chmod 600` 후 사용 — 단, Keychain 사용 우선)
- 키체인 항목을 팀원과 공유 (각자 자기 머신에 별도 등록)
- `security` 명령 결과를 그대로 로그/리뷰 산출물에 남기기
- 운영 런타임 시크릿은 IRSA/Secrets Manager로 주입한다. 개인 키체인의 운영 DB 등록 범위는 §운영 DB 키체인 등록 준비의 두 대상에 한정한다.

## AI 도구 사용 시

- DB 계열 MCP 서버(postgres/mssql/mysql 등)는 사용하지 않는다 — `.claude/hooks/block-db-mcp.sh` 훅으로 기계 강제 + [AGENTS.md](../AGENTS.md) 선언. 자격증명을 MCP 설정에 박아두는 패턴 금지.
- AI 스킬이 자격증명을 조회해야 할 때는 `security find-generic-password ... -w` 한 줄 호출로 캡처해 즉시 소비. 응답·로그·위키 노트에 평문이 남지 않도록 한다.
- AI에게 키체인 항목을 새로 등록(`add-generic-password`)시키지 않는다 — 본인이 직접 등록.

### dev/staging DB 읽기 쿼리: 사전 동의

dev/staging DB 대상의 **읽기 전용 쿼리**(`SELECT`/`EXPLAIN`/`SHOW`/스키마 메타)는 본 정책 등록 시점에 **사전 동의된 것으로 간주**한다. 모든 `/ad:*` 스킬(work-prep, data-request, code-review 등)은 매 쿼리마다 사용자 확인을 받지 않고 바로 실행해도 된다.

근거:
- 읽기 쿼리도 부하·데이터 노출을 고려하되 개발 검증의 반복 확인 비용을 줄인다.
- 잦은 확인 인터럽트는 워크플로를 끊는다 — 사용자가 명시적으로 거부했다.
- `.claude/hooks/sqlcmd-readonly.sh`는 호환 파일명을 유지하며 `tools/db_sqlcmd_guard.py`를 실행한다. 리터럴 sqlcmd 개발 명령의 실수 방지 장치이고 DB 권한·네트워크 통제를 대신하지 않는다.

### 개발 DB 데이터 입력·수정·삭제

등록된 **dev** 대상에서 사용자 작업 목적에 필요한 `INSERT/UPDATE/DELETE`는 사전 동의된 것으로 간주한다. 해당 범위 안에서는 쿼리마다 재확인하지 않는다. staging·운영·DDL·SP·권한 변경에는 이 동의를 적용하지 않는다.

근거: 2026-10-14 사용자 명시 요청 — 개발은 INSERT·UPDATE·DELETE 허용, 스키마 변경은 별도 승인. 목적: 테스트 데이터 준비·수정·정리를 같은 작업에서 수행한다.

- 실행 전 실제 host/DB가 등록된 개발 대상인지 확인하고 대상 테이블·키 조건·예상 건수·복구 방법을 확보한다. 트리거·외부 전송·링크드 서버 등 운영 영향이 있거나 확인되지 않으면 그 영향부터 확인한다. 이유: 개발 DB의 DML도 외부 시스템에 부작용을 낼 수 있다.
- 기본: 작업 전체 100행 이하의 테스트 데이터 변경을 자동 처리한다. 100행 초과·건수 미확정·전체 수정/삭제는 범위와 복구 방법을 제시해 별도 승인을 받는다. 호출을 나누어 같은 작업 한도를 회피하지 않는다.
- UPDATE/DELETE는 식별 가능한 키 조건을 명시하고 동일 조건의 조회로 대상을 확인한다. 실행 후 반영 건수와 결과를 확인하고 예상과 다르면 자동 재시도를 중단한다. 이유: WHERE의 존재만으로 변경 범위가 보장되지는 않는다.
- 자격증명은 기존 OS 금고를 사용하고 개발 전용 계정에는 필요한 테이블의 SELECT/INSERT/UPDATE/DELETE와 아래 실행기의 메타데이터 검사 권한을 구분해 부여한다. 현재 계정이 읽기 전용이면 권한 담당자가 별도로 설정한다. 에이전트가 권한을 확대하지 않는다.
- 작업 기록에는 대상·변경 종류·건수·복구 방법을 남기고 민감 원문 dump는 남기지 않는다. 정리는 키가 지정된 DELETE로 수행하며 TRUNCATE는 스키마/관리 작업의 별도 승인 경로에 둔다.

#### 로컬 실행기와 훅의 적용 범위

훅은 등록된 cool-dev 호스트와 `WebCatalog/ToBe/Community/WebLog/WebMarket`를 명시한 `sqlcmd -S … -d … -Q …`의 한 문장 SELECT를 처리하고 직접 DML은 `tools/db_execute.py`로 안내한다. 다른 dev 엔진·staging 호스트를 추가할 때는 대상과 도구 경로를 검토해 등록한다. 접속 대상 미확인·운영 호스트·대화형 실행·배치·원격 참조는 자동 경로 밖이다.

기본: 개발 DML은 전용 실행기에 작업 ID(`--task`), 등록 DB(`--database`), 사용자(`--user`)와 stdin SQL 한 문장을 전달한다. 비밀번호는 `SQLCMDPASSWORD` 환경변수를 쓴다. 실행기는 개발 host를 고정하며 운영 접속 옵션을 제공하지 않는다. 열을 지정한 리터럴 INSERT VALUES, 단일 테이블 UPDATE/DELETE를 지원한다. 수정값은 리터럴, 대상 조건은 `열 = 값` 또는 `열 IN (값 목록)`을 AND로 연결한다. 실제 키 여부와 업무 대상은 실행 전 확인한다.

실행기는 트랜잭션 안의 실제 영향 행 수를 검사해 남은 작업 예산을 초과하면 전체 롤백한다. 같은 작업 ID의 누적 커밋 행 수를 로컬 SQLite 원장(`~/.local/state/team2/db-execution.sqlite3`)에 기록하고 진행 중 실행과 불명확한 커밋 결과가 있으면 후속 실행을 차단한다. DB가 달라도 같은 논리 작업은 같은 ID를 유지한다. 이유: 호출·DB·재시도로 쪼개어 작업당 100행을 초과하는 실수를 막는다. 원장에는 SQL 해시·상태·건수만 기록하며 원문 SQL과 비밀번호는 저장하지 않는다.

시간 초과·연결 단절·커밋 응답 유실은 성공으로 처리하지 않는다. 불명확 상태는 자동 재시도 없이 담당자가 실제 반영 결과와 세션 정리를 대조한 뒤 별도 복구 절차로 다룬다. 작업 ID 변경이나 원장 삭제로 재실행하지 않는다. 이유: 커밋 이후 응답만 유실된 경우 중복 변경을 일으킬 수 있다.

실행기 메타데이터 검사에는 개발 계정의 DB `VIEW DEFINITION` 권한이 필요하다. 활성 트리거·연쇄 외래키 변경·temporal 테이블·뷰는 자동 DML 대상에서 제외한다. 담당자가 권한과 스키마를 준비하며 에이전트가 직접 권한을 확대하지 않는다. 복잡한 DML·트랜잭션 스크립트·DDL/SP는 검토된 수동 실행 절차로 넘긴다. 승인을 받았다는 문자열이나 환경변수로 훅을 우회하지 않는다 — 로컬 도구에는 승인 검증 기능이 없기 때문이다.

이 메타데이터 권한은 다른 테이블의 incoming FK를 빠짐없이 확인하는 대신 개발 DB 전체 SP 정의 등도 읽을 수 있게 한다. 정의에 민감정보가 있는 DB는 현재 실행기 대상으로 개통하지 않고 별도 최소권한 검토 경로를 사용한다. 이유: 객체 단위 권한만으로 보이지 않는 연쇄 변경을 안전하다고 판정할 수 없다. 실행기는 1초 잠금 대기 제한 아래 대상 테이블의 배타 잠금을 먼저 얻고 트랜잭션 안에서 메타데이터를 다시 검사한다. 개발 동시 쓰기와 충돌하면 실패 처리하며 실제 운영에는 이 잠금 방식을 적용하지 않는다.

훅은 임의 셸 스크립트·다른 드라이버·별칭의 실행을 포괄하지 못하고 로컬 실행기·원장은 사용자가 수정할 수 있다. 따라서 이 경로의 행 수 제한은 실수 방지 장치이며 모든 DB 접속의 보안 경계가 아니다. 실제 DB 계정 권한은 별도 방어선이다. Claude/Codex 각각 실제 훅 발화 검증 전에는 자동 강제가 완료되었다고 표시하지 않는다.

**여전히 확인 필수**인 항목:

- `MERGE/DDL/SP/권한 변경`, staging의 모든 데이터 변경, 위 개발 사전 동의 범위를 벗어난 변경 — SQL 전문(민감값은 보호 경로) + 예상 건수 + 복구 방법을 보여주고 확인.
- 운영(prod) DB — [운영 DB 접근 정책](./production-db-access-policy.md)의 개통·작업 승인 경로로 다룬다. 현재 미개통이며 데이터 추출은 [data-request-policy.md](./data-request-policy.md)도 함께 따른다.
- 결과 row 수가 폭주(>10만)할 가능성이 있는 SELECT — 사전에 카운트 쿼리로 가늠 후 본 쿼리 실행.
- 위키/노트에 결과 row dump를 남기는 행위 — 항상 요약(스키마/카운트/대표 패턴)만.

## 분실/회전

- 비밀번호 회전 시 키체인 항목도 `security add-generic-password -U`로 갱신.
- 머신 분실/매각 시 키체인 잠금 + 회전. §운영 DB 키체인 등록 준비에 따라 운영 DB 항목을 보관했다면 해당 자격증명도 회전한다.
