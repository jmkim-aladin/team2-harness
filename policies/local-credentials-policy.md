# 로컬 자격증명 정책 (macOS Keychain)

로컬 개발 환경에서 개발(dev)/스테이징(staging) DB·외부 API 자격증명을 다룰 때의 규칙. 운영 자격증명과 런타임 시크릿 주입은 [aws-secrets-convention.md](./aws-secrets-convention.md), 일반 보안 규칙은 [security-policy.md](./security-policy.md)를 따른다.

## 범위

- 대상: 팀원 본인 개발 머신에 한정.
- 저장 매체: macOS Keychain (login 키체인 권장). `~/.env`, 평문 파일, 프로젝트 디렉터리, vault, 하네스 저장 금지.
- 보관 가능: dev/staging DB 비밀번호, dev 외부 API 키, 로컬 도구 토큰(YouTrack, GitHub, 사내 시스템 등).
- 보관 금지: 운영 DB 비밀번호, 운영 API 시크릿, 타인 계정 자격증명, 결제·개인정보 관련 운영 자격증명.

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

`account` 필드는 DB 사용자명 또는 본인 사번/이메일을 사용한다 (`jmkim@aladin.co.kr` 등).

## 저장

GUI(키체인 접근.app)로 직접 등록하거나 CLI로:

```bash
security add-generic-password \
  -s "sm-max-admin-dev-database-read" \
  -a "$(whoami)" \
  -w '비밀번호'        # -w 뒤 공백 후 입력하면 history에 안 남는 셸도 있음. 가급적 빈 -w로 두고 프롬프트 입력.
```

업데이트는 `-U` 플래그. **단일 따옴표로 감싸 셸 history 노출을 줄인다**. `set -o history` 비활성 셸에서만 직접 인자 입력.

## 조회

표준은 `security find-generic-password` CLI.

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

- 환경변수에 두고 즉시 `unset`. 셸 history에 평문이 남지 않도록 한다.
- `tee`, `>` 리다이렉트, 임시 파일 저장 금지.
- 결과 화면에 비밀번호가 echo되지 않도록 `-w`만 캡처해 변수로 받는다.

## 금지

- 비밀번호를 위키/하네스/Slack/티켓에 평문 붙여넣기 (요청 시 마스킹 후 공유)
- `~/.netrc`, `~/.my.cnf`, `~/.pgpass` 등 평문 파일에 운영 자격증명 저장 (dev는 부득이할 경우 `chmod 600` 후 사용 — 단, Keychain 사용 우선)
- 키체인 항목을 팀원과 공유 (각자 자기 머신에 별도 등록)
- `security` 명령 결과를 그대로 로그/리뷰 산출물에 남기기
- 운영(prod) 자격증명을 Keychain에 넣기 — 운영은 IRSA/Secrets Manager만, 사람이 직접 보유하지 않는다

## AI 도구 사용 시

- DB 계열 MCP 서버(postgres/mssql/mysql 등)는 사용하지 않는다 (글로벌 메모리 정책). 자격증명을 MCP 설정에 박아두는 패턴 금지.
- AI 스킬이 자격증명을 조회해야 할 때는 `security find-generic-password ... -w` 한 줄 호출로 캡처해 즉시 소비. 응답·로그·위키 노트에 평문이 남지 않도록 한다.
- AI에게 키체인 항목을 새로 등록(`add-generic-password`)시키지 않는다 — 본인이 직접 등록.

## 분실/회전

- 비밀번호 회전 시 키체인 항목도 `security add-generic-password -U`로 갱신.
- 머신 분실/매각 시 키체인 잠금 + 회전. 운영 자격증명은 어차피 본 정책 범위 밖이므로 추가 조치 불필요.
