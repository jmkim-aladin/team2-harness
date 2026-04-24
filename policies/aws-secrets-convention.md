# AWS Secrets Manager 컨벤션

> 전사 암호화 가이드: [REF-A-729](https://aladincommunication.youtrack.cloud/articles/REF-A-729) (YouTrack KB)
> 참조 구현: naru (`NaruServer/apps/common/src/main/kotlin/.../config/secrets/`), max (`MaxServer/platforms/secrets/`)

## 네이밍 규칙

```
sm-{서비스}-{모듈}-{환경}-{리소스}
```

| 세그먼트 | 설명 | 예시 |
|----------|------|------|
| `sm` | Secrets Manager 접두어 (고정) | `sm` |
| `{서비스}` | 서비스 ID (catalog 기준) | `naru`, `bazaar`, `max`, `tobe`, `aasm` |
| `{모듈}` | 서비스 내 모듈/앱 | `sso`, `account`, `batch`, `web` |
| `{환경}` | 배포 환경 | `local`, `dev`, `prod` |
| `{리소스}` | 시크릿 종류 | 아래 표 참조 |

### 리소스 타입

| 리소스 | 용도 | 예시 |
|--------|------|------|
| `database-write` | Primary DB 쓰기 DataSource | `sm-naru-sso-prod-database-write` |
| `database-read` | Primary DB 읽기 DataSource (Read Replica) | `sm-naru-sso-prod-database-read` |
| `database-read-{이름}` | 추가 DB 읽기 전용 DataSource | `sm-max-admin-dev-database-read-webcatalog` |
| `database-write-{이름}` | 추가 DB 쓰기 DataSource | (필요 시) |
| `cache` | Redis/Valkey 캐시 | `sm-naru-sso-prod-cache` |
| `kms` | AWS KMS 암호화 키 | `sm-naru-sso-prod-kms` |
| `jwt-secret-key` | JWT 서명 키 | `sm-naru-sso-prod-jwt-secret-key` |
| `encryption-key` | 앱 레벨 암호화 키 (AES 등) | `sm-aasm-web-prod-encryption-key` |
| `service-endpoint-{대상}` | 외부 API 크레덴셜 | `sm-naru-sso-prod-service-endpoint-aladin-shopping` |

> **database 리소스 네이밍 규칙:**
> - `database-write` / `database-read` — 서비스 주 DB (이름 생략)
> - `database-read-{이름}` / `database-write-{이름}` — 추가 DB (DB명으로 식별)
> - 읽기/쓰기 구분은 DataSource 용도를 나타냄. 실제 접근 권한은 DB 계정에서 제어.

### 예시: naru 서비스 전체

```
sm-naru-local                                          # 로컬 (통합)
sm-naru-sso-dev-database-write                         # SSO API, dev, DB 쓰기
sm-naru-sso-dev-database-read                          # SSO API, dev, DB 읽기
sm-naru-sso-dev-cache                                  # SSO API, dev, 캐시
sm-naru-sso-dev-kms                                    # SSO API, dev, KMS
sm-naru-sso-dev-jwt-secret-key                         # SSO API, dev, JWT
sm-naru-sso-dev-service-endpoint-aladin-shopping-hr    # SSO API, dev, 쇼핑몰 HR
sm-naru-account-dev-database-write                     # Account API, dev, DB 쓰기
sm-naru-account-prod-database-write                    # Account API, prod, DB 쓰기
...
```

### 예시: bazaar 서비스

```
sm-bazaar-batch-dev-database-write
sm-bazaar-batch-dev-database-read
sm-bazaar-batch-dev-supplier-ashop                     # 알라딘 MSSQL (읽기 전용) — 레거시 네이밍
sm-bazaar-batch-dev-vendor-ebay                        # eBay API
sm-bazaar-batch-dev-vendor-st11                        # 11번가 API
```

### 예시: max 서비스

```
sm-max-admin-dev-database-write                        # PostgreSQL Primary (쓰기)
sm-max-admin-dev-database-read                         # PostgreSQL Read Replica (읽기)
sm-max-admin-dev-database-read-webcatalog              # MSSQL WebCatalog (읽기 전용)
sm-max-admin-dev-database-read-ebookcms                # MSSQL EbookCms (읽기 전용)
```

### 예시: aasm 서비스 (Node.js/Next.js)

```
sm-aasm-web-local-database-write                       # 로컬, DB
sm-aasm-web-local-jwt-secret-key                       # 로컬, JWT (NextAuth)
sm-aasm-web-local-encryption-key                       # 로컬, AES-256-GCM
sm-aasm-web-dev-database-write                         # dev, DB
sm-aasm-web-dev-jwt-secret-key                         # dev, JWT (NextAuth)
sm-aasm-web-dev-encryption-key                         # dev, AES-256-GCM
sm-aasm-web-prod-database-write                        # prod, DB
sm-aasm-web-prod-jwt-secret-key                        # prod, JWT (NextAuth)
sm-aasm-web-prod-encryption-key                        # prod, AES-256-GCM
```

> **Node.js 앱 참고:** Spring Boot의 `EnvironmentPostProcessor` 대신 `with-secrets.mjs` 래퍼 스크립트로
> 런타임에 시크릿을 fetch하여 `process.env`에 주입합니다. `APP_ENV` 환경변수로 프로파일을 구분합니다.

## JSON 구조

### database-write / database-read / database-read-{이름} / database-write-{이름}

```json
{
  "url": "jdbc:postgresql://hostname",
  "port": 5432,
  "database": "dbname",
  "username": "username",
  "password": "password"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `url` | string | O | JDBC 접속 URL (호스트만 또는 완전한 URL) |
| `port` | number | O | 포트 (1-65535) |
| `database` | string | O | 데이터베이스 이름 |
| `username` | string | O | 사용자명 |
| `password` | string | O | 비밀번호 |
| `driverClassName` | string | - | JDBC 드라이버 클래스 (앱 코드에서 기본값 제공, 생략 권장) |

> **url 형식:** 호스트만 제공 시 앱에서 `port`, `database`를 조합하여 완전한 JDBC URL 생성. 완전한 URL 제공 시 그대로 사용.
> **driverClassName 생략 권장:** 드라이버 클래스는 빌드 타임에 결정되는 기술 설정이므로 앱 코드에서 관리. 시크릿에 포함하면 인프라팀이 Java 클래스명을 관리해야 하므로 오류 가능성 증가.

### cache (Redis/Valkey)

```json
{
  "host": "hostname",
  "port": 6379,
  "password": "",
  "region": "ap-northeast-2"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `host` | string | O | 호스트명 |
| `port` | number | O | 포트 (1-65535) |
| `password` | string | - | 비밀번호 (빈 문자열 허용) |
| `region` | string | O | AWS 리전 |

### kms

```json
{
  "masterKeyId": "key-id-or-arn",
  "region": "ap-northeast-2"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `masterKeyId` | string | O | KMS 키 ID 또는 ARN |
| `region` | string | O | AWS 리전 |

### jwt-secret-key

```json
{
  "secretKey": "base64-encoded-key-minimum-32-chars"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `secretKey` | string | O | Base64 인코딩, 최소 32자 |

### encryption-key

```json
{
  "encryptionKey": "hex-encoded-key"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `encryptionKey` | string | O | 암호화 키 (AES-256: 64자 hex = 32바이트) |

### service-endpoint-{대상} (API 크레덴셜)

```json
{
  "apiKey": "ak_xxxxx",
  "apiSecret": "",
  "clientId": "client_xxxxx",
  "clientSecret": "sk_xxxxx",
  "hmacKey": ""
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `apiKey` | string | O | API 키 |
| `apiSecret` | string | - | API 시크릿 (빈 문자열 허용) |
| `clientId` | string | - | 클라이언트 ID |
| `clientSecret` | string | - | 클라이언트 시크릿 |
| `hmacKey` | string | - | HMAC 키 (빈 문자열 허용) |

## 구현 패턴

### application.yml 설정

```yaml
# naru
naru:
  aws:
    secrets-manager:
      enabled: true
      region: ap-northeast-2
      secret-name-prefix: sm-{서비스}-{모듈}-{환경}
      fail-on-error: true       # prod: true, local: false

# max
max:
  aws:
    secrets-manager:
      enabled: true             # 기본값: false (명시적 opt-in 필수)
      region: ap-northeast-2
      secret-name-prefix: sm-{서비스}-{모듈}-{환경}
      fail-on-error: true
      retry:
        max-attempts: 3         # 최초 시도 포함 총 횟수
```

### 로딩 방식

Spring Boot `EnvironmentPostProcessor`로 앱 시작 전에 로딩:

1. `secret-name-prefix`를 기반으로 시크릿 이름 구성
2. AWS Secrets Manager API로 JSON 조회
3. 타입별 데이터 클래스로 역직렬화
4. Spring Environment에 프로퍼티로 주입
5. `${...}` 플레이스홀더로 application.yml에서 참조

### 환경별 차이

| 항목 | local | dev | prod |
|------|-------|-----|------|
| prefix | `sm-{서비스}-local` | `sm-{서비스}-{모듈}-dev` | `sm-{서비스}-{모듈}-prod` |
| endpoint | LocalStack (`localhost:4566`) | AWS | AWS |
| 인증 | static credentials | IRSA | IRSA |
| fail-on-error | false | true | true |
| DB pool | 5 / 2 (max/min) | 20 / 5 | 30 / 10 |

### 보안 규칙

- 시크릿 값은 **절대 로그에 출력하지 않음** (이름만 로그)
- 데이터 클래스 `toString()`에서 민감 필드 마스킹
- 코드/문서에 실제 값 커밋 금지
- 로컬 개발은 LocalStack 사용

## 신규 서비스 시크릿 생성 체크리스트

- [ ] 네이밍 규칙 준수: `sm-{서비스}-{모듈}-{환경}-{리소스}`
- [ ] JSON 구조가 위 스키마와 일치
- [ ] dev/prod 환경 모두 생성
- [ ] IAM 정책에 시크릿 접근 권한 추가
- [ ] application-{env}.yml에 `secret-name-prefix` 설정
- [ ] fail-on-error: prod는 true
