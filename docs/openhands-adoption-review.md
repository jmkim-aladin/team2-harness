# OpenHands 도입 검토

> 검토일: 2026-09-27
> 범위: OpenHands Agent Canvas, Automation Service, Software Agent SDK, ACP 연계
> 방법: 공식 문서·공식 저장소·태그 소스의 읽기 전용 정적 검토. 설치와 실제 실행은 하지 않음.
> 기준 버전: Agent Canvas v1.24.0 / SDK v1.49.6 / Automation 1.15.1.
> 사용자 경계(2026-09-27): 외부 시스템은 조회만 한다. 실험 산출물은 격리된 로컬 변경·검증 기록이며 YouTrack 티켓·댓글·상태, GitHub PR·리뷰 댓글·push·merge, 외부 메시지·DB·배포는 변경하지 않는다. 외부 쓰기가 기본인 예제는 그대로 실행하지 않는다 — 사용자 명시 지시를 지키기 위한 경계다.

## 설치 전 보안·라이선스 판단

**판단: 검토한 공개 구성요소의 라이선스는 사내 사용을 허용한다. 회사 계정 사용도 확인했다. 다만 실제 업무 연결 전에는 아래 실행 권한과 데이터 경계를 검증해야 한다.** 이번 검토에서는 설치·실행·인증 정보 열람·외부 변경을 하지 않았다.

| 항목 | 확인 결과와 적용 조건 |
|---|---|
| 오픈소스 라이선스 | Canvas v1.24.0, SDK v1.49.6, Automation 1.15.1의 루트 LICENSE는 MIT다. 사내 상업적 사용·수정이 가능하며 사본·상당 부분 배포 시 저작권·허가 고지를 유지한다. 유료 서비스 계약과 전체 의존성 라이선스는 별도 범위다. |
| 회사 모델 계정 | 사용자 확인 완료. 정확한 요금제·계약의 데이터 처리 조건은 확인하지 않았다. 회사 계정이라는 사실만으로 개발 DB의 개인정보까지 외부 전송 가능한 것으로 해석하지 않는다. |
| 기존 로그인 재사용 | 원본 Claude Code를 본인 계정으로 공식 로그인하는 경로와 OAuth 토큰을 추출해 다른 앱에서 재사용하는 경로는 다르다. 전자를 기준으로 실제 ACP 어댑터 구현을 확인한다. 토큰 추출·복사 방식은 채택하지 않는다. |
| 실행 권한 | SDK의 ACP `request_permission`은 요청을 자동 승인한다. 기존 CLI의 승인창·팀 훅이 동일하게 작동한다고 가정할 수 없다. 외부 쓰기를 차단하는 실행 권한을 실제로 시험해야 한다. |
| 첫 실행 통계 | Canvas 소스에 동의 여부와 별개인 최초 설치 이벤트가 있다(DNT 예외). 플랫폼·브라우저·URL origin 등의 메타데이터이며 코드 전송 증거는 아니다. 첫 실행 전 `AGENT_CANVAS_DISABLE_TELEMETRY=1`을 적용하고 송신 여부를 확인한다. |
| 로컬·DB 경계 | 로컬 설치에서도 외부 모델을 쓰면 입력 코드·도구 결과가 모델 제공사로 전송된다. DB 읽기 전용 권한은 수정만 막는다. 첫 시험은 합성 자료로 하고 실제 DB 행 데이터와 광범위한 기존 자격 증명은 연결하지 않는다. |

로컬 정책은 비밀값의 로그·위키 기록을 금지하고 OS 비밀 저장소와 `tools/cred.py`를 통한 접근을 요구한다. 실행기에 전체 인증 저장소를 복사하는 대신, 필요한 조회 결과만 비밀값을 제거해 전달한다. 서버는 loopback에만 열고 격리된 시험 디렉터리에서 권한·맥락 유지부터 확인한다. [보안 정책](../policies/security-policy.md), [로컬 인증 정책](../policies/local-credentials-policy.md)

근거: [Canvas MIT](https://github.com/OpenHands/OpenHands/blob/v1.24.0/LICENSE), [SDK MIT](https://github.com/OpenHands/software-agent-sdk/blob/v1.49.6/LICENSE), [Automation MIT](https://github.com/OpenHands/automation/blob/1.15.1/LICENSE), [ACP 승인 코드](https://github.com/OpenHands/software-agent-sdk/blob/v1.49.6/openhands-sdk/openhands/sdk/agent/acp_agent.py#L1602-L1619), [통계 코드](https://github.com/OpenHands/OpenHands/blob/v1.24.0/src/services/telemetry.ts#L700-L756), [Claude 인증·약관](https://code.claude.com/docs/en/legal-and-compliance), [Codex 인증](https://learn.chatgpt.com/docs/auth).

확인 한계: 선택한 정책·공식 문서·고정 버전 소스의 정적 검토다. 전체 의존성 취약점·라이선스 검사, 실제 네트워크·권한 시험, 회사의 별도 보안 규정·계약 검토는 수행하지 않았다. 정식 보안감사나 법률 검토를 대신하지 않는다.

### YouTrack 등 외부 문서의 자동 변경 경로

이번 검토에서는 외부 문서·티켓·설정을 변경하지 않았고 OpenHands를 실행하지 않았다. 따라서 실제 환경에서 자동 변경이 차단된다는 실행 검증은 아직 없다.

- **자동화:** 공식 문서는 생성된 자동화가 기본 활성 상태이며 다음 예약에 실행된다고 설명한다. 작업은 저장된 secrets, MCP, 네트워크와 Git 제공자 로그인 토큰을 사용할 수 있다. 설치와 자동화 생성은 구분해야 하며, 첫 시험에서는 자동화·웹훅·외부 발행 플러그인을 구성하지 않는다. [공식 동작 설명](https://docs.openhands.dev/openhands/usage/automations/creating-automations)
- **대화 중 도구 실행:** 전용 YouTrack 연동이 없어도 셸에서 API 호출은 가능하다. 팀의 `tools/cred.py`는 macOS Keychain 조회 기능을 제공하고 `youtrack/api-guide.md`에는 쓰기 API 사용법도 있다. 같은 사용자 권한의 에이전트가 이 도구와 네트워크에 접근할 수 있으면 기존 인증을 이용할 가능성이 있다. 인증 도구는 실행하지 않았으며 현재 토큰 권한도 확인하지 않았다.
- **필요한 차단:** 초기 에이전트에는 티켓·위키의 필요한 로컬 사본만 전달한다. 외부 서비스에 대한 네트워크 접근과 기존 자격 증명 접근을 실행 환경에서 제한하고, 이후 조회가 필요하면 별도의 읽기 전용 수집 경로를 둔다. 프롬프트에 쓰기 금지를 적거나 토큰 파일을 읽기 전용으로 연결하는 것만으로는 충분하지 않다.
- **통과 기준:** 실제 YouTrack을 수정하는 시험 대신 로컬 모의 API에서 등록·수정·삭제 시도가 실행 전에 차단되는지 확인한다. 셸·MCP·기존 CLI 각각의 경로와 서버 재시작 후 제한 유지도 검사한다. 이 검증 전에는 실제 티켓·KB의 자동 변경 방지를 통과로 판정하지 않는다.

## 현재 우선순위

사용자 지시: 야간 예약 운영은 후순위다. 먼저 팀 하네스 정책과 티켓 위키를 근거로 업무를 지속하고, 세션·에이전트가 바뀌어도 필요한 맥락과 책임을 유지하는지 검증한다.

1. **하네스 적용:** 서비스 작업 공간에서도 team2 정책과 해당 티켓·서비스 규칙을 찾아 적용한다. 파일을 읽었다는 기록뿐 아니라 실제 결과가 규칙을 지켰는지 확인한다.
2. **업무 맥락 유지:** 티켓 목표, 기준 코드와 로컬 변경분, 현재 판단, 검증 근거, 남은 작업을 유지한다. 오래된 대화를 모두 재주입하는 것보다 현재 사실을 확인하고 이어받는 능력을 평가한다.
3. **명확한 오케스트레이션:** 업무마다 책임 실행자 한 명을 두고, 개발·리뷰의 입력과 종료 조건, 수정 요청의 반환 경로를 명확히 한다. 같은 파일을 중복 수정하거나 서로의 완료 선언만 받아들이는 흐름을 막는다.
4. **세션 전환과 인계:** 같은 세션 재개, 새로운 세션으로 인계, 다른 에이전트로 인계를 각각 시험한다. 변경된 코드에는 이전 리뷰·테스트 결과를 그대로 적용하지 않는다 — 코드와 근거의 일치를 지키기 위해서다.
5. **사람의 개입 감소:** 사용자가 같은 설명을 반복하거나 에이전트 사이에서 결과를 복사·전달하는 횟수를 측정한다. 실제 정책 결정만 간결하게 요청한다.

OpenHands는 이 기준을 시험할 후보로 유지한다. Agent Canvas와 SDK의 기능 존재만으로 위 조건을 충족했다고 판정하지 않는다. 처음에는 사람이 지켜보는 한 건의 업무를 끝까지 연결하며, 시간 예약과 대규모 병렬 실행은 이후에 평가한다.

## 인증을 고려한 설치 선택

사용자는 Hermes 사용 당시 모델 계정, GitHub·YouTrack 등 개발 도구, 개발 DB 전반에서 인증 연동의 한계를 겪었다고 확인했다. Claude·Codex는 회사 계정을 사용한다. 로컬 설치를 선택했으며, 설치보다 보안·라이선스 검토를 먼저 진행한다. 이후 시험에서는 실제 인증 경로와 권한 제한을 함께 확인한다.

- **ACP 모델 인증:** 공식 문서는 같은 머신에서 실행하는 CLI의 기존 로그인을 재사용한다고 안내한다. 특히 macOS Claude 로그인은 Keychain에 있으므로 홈 폴더를 Linux 컨테이너에 연결하는 것만으로 동일하게 재사용된다고 가정할 수 없다. 이 경로는 설치 후 인증 여부만 확인하고, 인증 파일·토큰 본문을 출력하지 않는다 — 자격 증명 노출을 막기 위해서다. [ACP 인증](https://docs.openhands.dev/openhands/usage/agent-canvas/acp-agents#authentication)
- **혼합 구성:** Agent Canvas와 Agent Server는 Mac에서 실행하고, native agent의 지원 파일·터미널 도구만 Docker로 분리하는 공식 모드가 있다. 대화·모델 호출·인증은 바깥 서버에 남는다. 지원되지 않는 도구는 호스트에서 실행될 수 있으며, 이 기능을 ACP CLI 전체의 격리 보장으로 해석하지 않는다 — 실제 도구 실행 경로가 다르기 때문이다. [Docker 실행 모드](https://docs.openhands.dev/openhands/usage/agent-canvas/backend-setup/docker-execution)
- **외부 시스템 인증:** 모델 로그인 재사용이 GitHub·YouTrack·사내 SSO·브라우저 세션의 연동을 뜻하지는 않는다. 기존 쓰기 가능한 인증을 실행기에 넘기기보다, 읽기 전용 수집 결과를 티켓 맥락으로 전달하는 방식을 우선 시험한다. 외부 쓰기 금지 조건은 유지한다.
- **업무 보존:** 위 혼합 모드의 실행 컨테이너는 기본적으로 임시 공간이다. 작업 파일은 지정한 로컬 작업 디렉터리에 보존해야 세션 전환 실험에서 손실 여부를 판단할 수 있다.

## 확인된 지원 범위

| 영역 | 공식 확인 | 팀 적용 판단 |
|---|---|---|
| 현재 운영면 | Agent Canvas가 대화, 파일, 터미널, 백엔드, 자동화를 관리하며 로컬·Docker·VM·Cloud를 선택한다. [공식 개요](https://docs.openhands.dev/openhands/usage/agent-canvas/overview) | Hermes를 즉시 폐기하기보다 후보 선정·YouTrack 수집은 기존 하네스에 두고 Canvas를 실행면으로 시험한다. |
| 예약 실행 | cron 자동화, 수동 실행, 과거 실행 대화와 JSON/CSV 이력을 제공한다. 각 실행은 새 sandbox에서 시작한다. [자동화 개요](https://docs.openhands.dev/openhands/usage/automations/overview), [관리](https://docs.openhands.dev/openhands/usage/automations/managing-automations) | “매일 밤 같은 큐에서 최대 N건”은 외부 선정기와 명시적 중복 방지 규칙이 필요하다. |
| 이벤트 실행 | GitHub 이벤트는 내장되고, 그 밖의 서비스는 서명 webhook을 등록한 뒤 자동화에 연결한다. [이벤트 자동화](https://docs.openhands.dev/openhands/usage/automations/event-automations) | YouTrack은 공식 문서에서 native connector를 확인하지 못했다. REST API 수집·상태 기록 어댑터를 별도로 둔다. |
| 코드 리뷰 | GitHub PR에 자동으로 inline review를 남기는 workflow/plugin이 제공된다. [PR 리뷰](https://docs.openhands.dev/openhands/usage/use-cases/code-review) | 외부 PR·댓글을 쓰는 예제는 그대로 사용하지 않는다. 리뷰는 별도 실행으로 로컬 변경분에 남기고 코드가 바뀌면 다시 실행한다 — 외부 쓰기 금지 지시를 지킨다. |
| 실행 검증 | QA plugin은 실제 앱을 실행해 HTTP·CLI·브라우저를 확인하고 PASS/FAIL/PARTIAL과 명령·출력·스크린샷을 기록한다. 테스트 suite·lint·typecheck 자체는 CI의 책임이다. [QA](https://docs.openhands.dev/openhands/usage/use-cases/qa-changes) | 레거시·현대 서비스별 검증 명령을 catalog에서 가져오되, 현재 기준 브랜치에서 실제 발견·실행된 경우만 통과로 기록한다. |
| SDK 영속성 | SDK는 `base_state.json`과 event 파일을 자동 저장하고 같은 `conversation_id`·영속 디렉터리로 복원할 수 있다. [Persistence](https://docs.openhands.dev/sdk/guides/convo-persistence) | 정상 종료 후 재개는 지원 사실이다. 프로세스 kill, sandbox 교체, 호스트 재부팅 후 재개는 별도 실험으로 판정한다. |
| sandbox | Docker backend는 Canvas·Agent Server·Automation Server를 포함할 수 있고, 설정/비밀/대화 기록과 프로젝트 mount를 별도로 보존하도록 안내한다. [Docker Canvas](https://docs.openhands.dev/openhands/usage/agent-canvas/backend-setup/docker) | 작업 저장소와 `.openhands` 상태를 영속 volume으로 분리하고, 서비스별 허용 경로만 mount한다. |

## 정확성에 영향을 주는 제약

### 실행 시간과 재시작

Automation 1.15.1의 기본 실행 시간은 10분, **기본 설정의 최대 허용 시간은 30분**이다. 소스는 `AUTOMATION_DEFAULT_RUN_DURATION`·`AUTOMATION_MAX_RUN_DURATION`으로 배포 설정을 바꿀 수 있음을 명시한다. 따라서 30분은 제품의 절대 상한이 아니다. 생성 문서는 기본 10분·최대 30분을 안내하므로 실제 설치의 설정을 확인해야 한다. [생성 문서](https://docs.openhands.dev/openhands/usage/automations/creating-automations), [공식 설정 소스](https://github.com/OpenHands/automation/blob/1.15.1/openhands/automation/config.py#L201-L237)

시간 설정을 늘리는 것만으로 장시간 작업의 복구·검증 완료까지 보장되지는 않는다. 한 티켓을 조사·수정·테스트·리뷰 단계로 나누고, 각 단계의 결과를 로컬 티켓 노트와 격리된 작업 디렉터리에 저장하는 방식으로 실험해야 한다.

현재 Automation Service 소스는 예약 시 PENDING run을 생성하고 dispatcher가 여러 run을 비동기 task로 실행한다. `create_pending_run()`에 해당 자동화의 활성 RUNNING run을 확인하는 로직은 보이지 않는다. [scheduler](https://github.com/OpenHands/automation/blob/main/openhands/automation/scheduler.py#L152-L245), [run 생성](https://github.com/OpenHands/automation/blob/main/openhands/automation/utils/run.py#L174-L221), [dispatcher](https://github.com/OpenHands/automation/blob/main/openhands/automation/dispatcher.py#L545-L617)

이는 “항상 중복된다”는 뜻은 아니지만, 실행 시간이 주기보다 길 때 자기 중첩을 자동으로 막는다고 가정할 근거가 없다는 뜻이다. 티켓 ID·저장소를 작업 소유권 키로 하고 기준 commit을 기록하는 team2 측 lease/lock을 먼저 둔다. 실패 run은 재시도하되 최대 횟수·간격·중복 작업 방지 규칙을 하네스에 명시한다. 공식 자동화 저장소는 현재 Beta이고, retry 정책은 deployment/runtime 설정과 구현을 확인해야 한다. [Automation Service](https://github.com/OpenHands/automation#readme)

SDK의 정상적인 pause/resume와 영속 디렉터리를 통한 대화 복원은 지원된다. 그러나 ACP(Claude Code, Codex, Gemini CLI)는 별도 세션 파일을 사용한다. **과거 이슈 #14260(2026-06-04 종료)**은 당시 sandbox recycle 후 `acp_session_id`와 ACP 자체 세션 파일이 사라져 native `session/load`만으로는 복원이 되지 않는다고 설명한다. 이 이슈는 bootstrap resume이 PR #14295로 반영됐다고 명시한다. 이 방식은 이전 메시지를 다시 주입하므로 tool-call provenance와 sandbox 파일 상태를 잃을 수 있다고도 기록되어 있다. 종료된 이슈를 현행 미해결 버그의 증거로 쓰지 않으며, native 세션 복원과 작업 파일 보존의 현재 동작은 실험에서 확인한다. [공식 이슈 #14260](https://github.com/OpenHands/OpenHands/issues/14260)

### 승인과 ACP 권한 경계

native OpenHands SDK에는 `AlwaysConfirm`, `NeverConfirm`, `ConfirmRisky` 정책과 대기 중 action을 사람이 승인·거절하는 handler가 있다. [Security & Action Confirmation](https://docs.openhands.dev/sdk/guides/security)

반면 OpenHands SDK v1.49.6의 `ACPAgent` 소스는 `request_permission()`에서 ACP가 보낸 permission options의 첫 항목을 선택해 자동 승인한다. 소스의 함수 주석도 “Auto-approve all permission requests”라고 명시한다. [v1.49.6 `acp_agent.py` L1602-L1619](https://github.com/OpenHands/software-agent-sdk/blob/v1.49.6/openhands-sdk/openhands/sdk/agent/acp_agent.py#L1602-L1619)

따라서 Claude/Codex를 ACP로 연결하면 기존 팀의 승인 규칙이나 파일·명령 권한 정책이 그대로 전달된다고 보면 안 된다. 초기 실험은 native agent의 제한된 Docker sandbox로 하고, ACP는 읽기·분석 작업부터 별도 검증한다. ACP 경로에서 실제 코드 쓰기·외부 API 쓰기·배포 명령의 승인/거절을 어떻게 보장할지는 추가 실행 검증 전까지 미확인이다.

### 지식과 skill 경계

SDK v1.49.6의 프로젝트 skill 탐색 위치는 `{work_dir}/.agents/skills/`, `.openhands/skills/`, 레거시 `.openhands/microagents/`와 Git root다. [공식 `skill.py` L1049-L1069](https://github.com/OpenHands/software-agent-sdk/blob/v1.49.6/openhands-sdk/openhands/sdk/skills/skill.py#L1049-L1069)

team2의 핵심 규칙과 `/ad:*` alias는 주로 `.codex/skills/`에 있으므로 자동 인식·동일 동작을 가정할 수 없다. OpenHands용으로 짧은 `AGENTS.md`와 명시적 `.agents/skills/` adapter를 두고, 실제 하네스 문서를 읽는 경로를 별도로 매핑해야 한다. ACP-backed conversation은 OpenHands가 파일 도구를 소유하지 않아 path-triggered rules가 주입되지 않는다는 공식 문서도 있다. [skill 주입 동작](https://docs.openhands.dev/sdk/guides/skill#path-triggered-rules)

### 서비스별 검증 가능성

team2 catalog의 shopping 서비스는 Windows 전용·VB6 IDE 의존이며 macOS에서 빌드·테스트를 실행할 수 없고, test runner도 없다고 기록한다. [shopping catalog](../catalog/shopping.yaml#L120)

max catalog에는 테스트 명령이 적혀 있지만, 2026-09-27 정적 확인에서 현재 `release/v2026.9.11`의 `maxcms-api@15d5f8f52abe53f5dbaed7b2b21cd23b3bd947d3`에는 catalog가 가리키는 테스트 프로젝트·solution 포함을 확인하지 못했다. `MaxServer@18d6e17d0746fb67a5577333c9a15f9c81c8ef5f`에는 `src/test`와 Gradle 명령이 보이지만 아직 실행하지 않았다. 그러므로 catalog의 명령 존재만으로 야간 검증 완료를 표시할 수 없다. 실제 기준 브랜치에서 테스트가 발견되고, 실행 수가 0보다 크며, 같은 기준 commit·변경분 해시에서 통과한 경우에만 해당 테스트 범위의 PASS로 기록한다. 테스트 개수만으로 요구사항 충족을 대신하지 않으며, 완료 조건별 근거를 확인한다.

## 권장 도입 실험

**목표:** 실제 YouTrack 티켓 한 건을 외부 변경 없이 분석·수정·검증·독립 리뷰하고, 중간 인계에서도 사용자의 재설명 없이 이어간다. 아직 실행하지 않은 실험안이다.

1. YouTrack을 읽기 전용으로 조회하고 로컬 티켓 위키와 현재 소스를 대조한다. 최신 요구사항과 남은 확인을 정리한 뒤 기존 티켓 노트에 현재 작업 요약을 유지한다.
2. OpenHands의 격리된 작업 공간에 team2 정책·필요한 서비스 지식·티켓 노트 읽기 경로를 연결한다. 수정본은 로컬에 남기고 외부 쓰기 자격 증명은 전달하지 않는다 — 사용자의 외부 변경 금지 지시를 따른다.
3. 개발 중 멈췄다가 같은 세션을 재개하고, 별도로 새 세션에도 인계한다. 이어받은 에이전트가 목표·현재 변경분·미확인 사항·다음 행동을 정확히 파악하는지 확인한다.
4. 별도 리뷰 실행에 티켓 요구사항·같은 코드 버전·테스트 근거를 전달한다. 개발자의 결론을 그대로 넘겨받지 않고 요구사항과 코드를 대조하며, 지적은 개발 실행으로 돌려보낸다. 수정 후 새 변경분을 재검증한다.
5. 사람에게 변경 이유, 로컬 diff, 실제 검증 결과, 남은 확인만 짧게 인계한다. 티켓·댓글·PR·push·merge·외부 메시지·DB·배포는 이 실험에서 변경하지 않는다 — 읽기 전용 외부 연계 범위를 지킨다.

### 실험 통과 조건

- 새 세션이 하네스 정책과 원본 티켓을 스스로 찾아 사용자의 재설명 없이 이어간다.
- 같은 세션 재개와 새 세션 인계에서 작업 파일·현재 상태·다음 행동이 일치한다. 대화가 보이는 것만으로 복구 통과로 판정하지 않는다 — 실제 업무 지속성을 확인하기 위해서다.
- 담당 실행자·개발/리뷰 단계·지적 반환 경로가 기록되며, 동일 티켓을 중복 실행하지 않는다.
- 개발·테스트·리뷰가 동일한 기준 commit·로컬 변경분 해시에 연결된다. 테스트 미실행·0건·부분 검증은 그대로 구분한다.
- 위키와 현재 소스가 다르면 차이를 기록하고 검증한다. 과거 완료 기록을 현재 통과 근거로 재사용하지 않는다 — 최신 코드와 증거를 맞추기 위해서다.
- 승인·거절 동작은 로컬 모의 도구로 확인하고, 외부 시스템에는 쓰기가 발생하지 않는다.
- 사람의 재설명·중간 전달 횟수, 검토 시간, 재작업, 실행 비용을 기존 방식과 비교한다.

## 도입 판단

첫 판단 기준은 예약 실행이나 에이전트 수가 아니라 **팀 정책을 적용한 업무 지속성과 정확한 인계**다. 이 흐름이 통과하면 여러 티켓, 프로세스 장애 복구, 야간 예약 순서로 범위를 넓힌다. SOF는 개발 중이므로 준비된 명세를 입력으로 연결하는 후보로 두고 현재 도입의 전제조건으로 삼지 않는다.
