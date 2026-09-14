# 시크릿 매니저 설정 요청 티켓 템플릿 (개발3팀)

> 시크릿 매니저 키 생성은 **개발3팀** 영역이다. 개발2팀 몫은 구성 설계 · 생성 요청 · 반영 후 확인이다 — [policies/team-members.md](../../policies/team-members.md) §타팀 경계.
> 요청 티켓은 **DEV3 프로젝트**에 만든다. DEV2 Feature·Task 트리로 감싸지 않는다.
> 실례: DEV3-2089 (`aladin-aws-b2b 환경 내 Secret Manager 설정 요청`)

## 필드

| 필드 | 값 |
|------|-----|
| 프로젝트 | DEV3 |
| 제목 | `{{서비스}} {{환경}} Secret Manager 설정 요청` |
| 유형 | Task |
| 우선순위 | Normal |
| 담당팀 | 개발3팀 |
| Assignee | {{개발3팀 담당자}} |
| 관련팀 | 개발3팀 |
| Platform | Server |
| Infra | `AWS - 신규` (신규 Secret 생성) / `AWS - 기존` (기존 값 변경) |
| Service | 비움 (DEV3 프로젝트 기준) |
| CC | 비움 (요청자가 명시할 때만) |

- reporter는 토큰 owner로 박히므로 **생성 전 본인 계정인지 확인**한다 — [youtrack/api-guide.md](../../youtrack/api-guide.md) §토큰 owner 규칙.
- 개발2팀 쪽 반영·확인 작업을 이 티켓에 섞지 않는다. 필요하면 DEV2에 별도로 만들고 대기 구간을 본문에 남긴다.

## 본문

본문은 **What / Why / Where / How** 4개 섹션이다. DEV2 Feature의 5W1H와 달리 Who·When은 쓰지 않는다.

```
{{서비스}} 서비스 {{환경}} 연동을 위해 아래와 같이 SM 설정 작업 요청 드립니다.

What(무엇)

* {{AWS 계정}} 계정의 AWS Secrets Manager에 {{용도}} Secret {{생성/값 변경}} 요청

Why(왜)

* {{이 인증 정보가 필요한 업무 맥락}}
* {{환경 분리·운영 개선 등 추가 사유}}

Where(어디)

* AWS Account: {{aladin-aws-xxx-dev / aladin-aws-xxx-prod}}
* Secrets Manager 리소스: {{Secret Name}} ({{신규/기존}})

How(어떻게)

* {{신규 Secret 생성 / 기존 Secret 값 변경}}
* Secret 항목 구성과 값은 보안상 메일로 별도 전달
* {{항목 구성 제약 — 예: 운영 Secret과 동일한 항목 구성으로 생성 필요}}
* 개발팀에서 {{환경}} 연동 테스트로 정상 동작 확인
* {{이번 요청 범위에서 제외하는 대상}}
```

## 작성 규칙

- **인증 정보 평문을 티켓 본문·댓글·메신저에 남기지 않는다.** 값은 메일 등 사내 보안 전달 수단으로 따로 보내고, 티켓에는 "메일로 별도 전달"만 적는다. 이슈 트래커는 검색·이력이 남고 CC 범위 밖에서도 조회된다.
- Secret Name은 인증 정보가 아니므로 Where에 적어 작업 대상을 특정할 수 있게 한다. 이름 자체를 감춰야 하는 건이면 이름도 메일로 뺀다.
- **환경을 한 티켓에 섞지 않는다.** dev와 prod를 같이 요청하면 반영 시점·승인 주체가 가려진다 — [docs/sprint/ticket-guide.md](../../docs/sprint/ticket-guide.md) §2-3.
- 항목 일부만 등록되면 나머지가 비어 인증 정보 구성이 깨지는 구조라면 How에 그 제약을 명시한다.
- 요청 회신까지는 **대기 구간**이다. 개발2팀 쪽 후속 작업 티켓이 있으면 그 본문 When/How에 대기 구간을 적는다.

## 추가 확인 사항

- 대상 서비스: {{서비스명}}
- AWS 계정: {{계정명}}
- 대상 환경: {{dev / prod}}
- 값 전달 수단: {{메일 등}}
- 후속 확인 주체: {{개발2팀 담당자}}
