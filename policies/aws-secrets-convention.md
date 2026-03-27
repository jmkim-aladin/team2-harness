# AWS Secrets Manager 컨벤션

> 전사 암호화 가이드: [REF-A-729](https://aladincommunication.youtrack.cloud/articles/REF-A-729) (YouTrack KB)
> 참조 구현: naru (`NaruServer/apps/common/src/main/kotlin/.../config/secrets/`)

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
| `database-write` | Primary DB (쓰기) | `sm-naru-sso-prod-database-write` |
| `database-read` | Read Replica DB (읽기) | `sm-naru-sso-prod-database-read` |
| `cache` | Redis/Valkey 캐시 | `sm-naru-sso-prod-cache` |
| `kms` | AWS KMS 암호화 키 | `sm-naru-sso-prod-kms` |
| `jwt-secret-key` | JWT 서명 키 | `sm-naru-sso-prod-jwt-secret-key` |
| `service-endpoint-{대상}` | 외부 API 크레덴셜 | `sm-naru-sso-prod-service-endpoint-aladin-shopping` |

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
sm-bazaar-batch-dev-supplier-ashop                     # 알라딘 MSSQL (읽기 전용)
sm-bazaar-batch-dev-vendor-ebay                        # eBay API
sm-bazaar-batch-dev-vendor-st11                        # 11번가 API
```

## JSON 구조

### database-write / database-read

```json
{
  "url": "jdbc:postgresql://hostname",
  "port": 5432,
  "database": "dbname",
  "username": "username",
  "password": "password",
  "driverClassName": "org.postgresql.Driver"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|:---:|------|
| `url` | string | O | JDBC 접속 URL |
| `port` | number | O | 포트 (1-65535) |
| `database` | string | O | 데이터베이스 이름 |
| `username` | string | O | 사용자명 |
| `password` | string | O | 비밀번호 |
| `driverClassName` | string | O | JDBC 드라이버 클래스 |

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
naru:
  aws:
    secrets-manager:
      enabled: true
      region: ap-northeast-2
      secret-name-prefix: sm-{서비스}-{모듈}-{환경}
      fail-on-error: true       # prod: true, local: false
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
