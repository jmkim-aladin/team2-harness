# 보안/시크릿 정책

> 전사 암호화 가이드: [REF-A-729](https://aladincommunication.youtrack.cloud/articles/REF-A-729) (YouTrack KB)
> 하위: 비대칭키(REF-A-730), 대칭키(REF-A-735), Browser(REF-A-739), Sequence Diagram(REF-A-760)

## 시크릿 관리

- 시크릿(API 키, DB 패스워드, 토큰 등)은 절대 코드/문서에 커밋하지 않는다
- `.env`, `credentials.json` 등은 `.gitignore`에 반드시 포함
- 환경별 시크릿은 GitHub Environments 또는 별도 시크릿 관리 시스템 사용
- config(설정)은 공유 가능, secret(시크릿)은 로컬/환경별 분리

### 취급 공통 원칙 (SoT — 모든 시크릿 정책에 적용)

- 값은 로그·화면·리뷰 산출물·위키에 남기지 않는다 — 이름만 기록, 민감 필드는 마스킹
- 평문 파일 대신 전용 저장소 사용 (운영: AWS Secrets Manager / 로컬: macOS Keychain)
- 셸 전달은 프롬프트 입력 또는 환경변수로 — 인자 평문 전달은 `ps`·history에 노출된다. 사용 후 즉시 `unset`

대상별 상세: [aws-secrets-convention.md](./aws-secrets-convention.md) · [local-credentials-policy.md](./local-credentials-policy.md) · [datadog-api-policy.md](./datadog-api-policy.md)

## 인증/권한

- 공통 인증/권한/감사로그는 edge(API Gateway/BFF)에서 통일
- 서비스 간 통신은 내부 인증 토큰 사용
- 운영 서비스는 기능보다 **추적 가능성**이 더 중요

## 코드 보안

- OWASP Top 10 취약점 주의 (SQL Injection, XSS 등)
- 특히 레거시 SP 호출 시 파라미터 바인딩 필수
- 외부 입력은 반드시 검증 후 사용
