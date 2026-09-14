# pstack 지침·검증 도구 적용 기록

2026-09-14, 사용자의 “전체 적용” 요청에 따라 [적용 초안](pstack-harness-block-adoption-draft.md)의 B01–B10을 반영했다. 검토 원본은 [pstack 고정 커밋](https://github.com/cursor/plugins/tree/5bf2b1544db739998121a306340631963c2ff3de/pstack)이며, 기존 팀 하네스의 소비 지점과 SoT에 맞춰 변형했다.

## 반영 내역

| 블록 | 적용한 동작·규칙 | 실제 위치 |
|---|---|---|
| B01 | 원칙 이름·자기 보고 대신 도구 호출·참조·산출물로 효과 확인 | [스킬 작성 원칙 §3](../policies/skill-authoring-principles.md#3-유도--목표-행동을-익숙한-용어로-짧게-전달한다) |
| B02 | 발동 사례·동일 조건·블라인드 비교, 단일 일치로 삭제 확정 금지 | [거버넌스](../policies/harness-governance-policy.md#변경-통제), [감사 command](../.claude/commands/ad/harness-optimize.md), [행동 평가 가이드](harness-behavior-evaluation.md) |
| B03 | 완료 조건과 실제 관찰·근거 연결 | [DoD](../templates/dod-checklist.md), [PR 템플릿](../templates/pr-template.md) |
| B04 | 안전 판정의 핵심 가정을 작은 실행으로 확인하고 정적/실행/미확인 구분 | [코드 리뷰 §검증 순서](../.claude/commands/ad/code-review.md#검증-순서) |
| B05 | 현재 동작·과거 의도·추론·미검색/접근 불가/미발견 구분 | [work-prep 노트](sprint/work-prep-note-template.md#본문-템플릿) |
| B06 | 호출 누락·실행 실패·잘못된 SoT를 구분, 반복 오류는 도구화 검토 | [감사 command](../.claude/commands/ad/harness-optimize.md), [서비스 AGENTS 양식](../templates/service-harness/AGENTS.md.tmpl) |
| B07 | 반복 실패의 공통 전제와 관련 대상별 자원 분포를 재검토 | [mattpocock 오버라이드](../policies/overrides/mattpocock.md#디버깅--반복-실패의-공통-전제) |
| B08 | revision·미커밋 상태·환경·증거·다음 행동을 인계에 연결 | [증거 계약](agents/verification.md), [plan-run](../.claude/commands/ad/plan-run.md), [completion 설정](../configs/discord-agent-profiles.yaml) |
| B09 | 실행·준비 확인·사용자 경로·증거·정리와 문서/도구/제품 오류 구분 | [실행 계약 양식](../templates/service-harness/VERIFICATION.md.tmpl), [카탈로그](../catalog/README.md#실제-실행-검증-계약), [실제 CLI 계약](verification/harness-links.md) |
| B10 | 도구화의 수용 기준을 실제 실행·재실행·재개·증거 보존으로 고정 | [감사 command](../.claude/commands/ad/harness-optimize.md), [링크 검증 도구](../tools/verify_harness_links.py), [행동 평가 도구](../tools/evaluate_harness_behavior.py) |

Codex alias는 source command를 읽는 구조를 사용한다. 오래된 `.agents/skills/source-command-ad-code-review` 본문도 같은 command로 연결하고 해당 이름을 명시한 경우만 호출되도록 좁혔다. vendor handoff에는 팀 오버라이드를 읽는 포인터 한 줄만 추가하고 등록부에 남겼다. 전역 AGENTS/CLAUDE에는 본문을 복제하지 않았고, 작업 시작 전에 있던 별도 변경을 보존했다. 커밋·push·PR·외부 게시·서비스 배포는 수행하지 않았다.

## 검증

- 최종 `python3 -m unittest discover -s tests`: **전체 230개 통과**. 최초 32개 대상 검사 후 전체 회귀와 실제 소비 경로까지 검증했다. 명령·원본 결과·현재 파일 digest는 [검증 증거](verification/pstack-2026-09-14-results.json)에 기록했다.
- 실제 `sync_harness_links.py` CLI를 독립 임시 catalog/vault에서 실행해 PASS. 기본 dry-run의 파일·git 상태 보존, 실제 카탈로그 값 반영, 생성 영역 밖 내용 보존, 반복 실행·재개, 관리 영역 없는 문서 보존을 확인했다. fixture 정리 후 원본 로그·전후 문서를 다시 읽었다.
- evaluator는 직접 산출물을 읽고 거짓 assertion, 누락·실행 실패, 조건 불일치, 경로 탈출, boolean/숫자 혼동, 증거 덮어쓰기를 구분하는 테스트를 통과했다. 성공 문자열·receipt의 자기 보고만으로 통과시키지 않는다.
- 독립 코드 리뷰에서 미확인 조건의 오통과, 조건 키의 누락/null 혼동, 관찰 실패가 미확인에 가려지는 판정, 실행 후 데이터 손상 분류를 수정했다. 최종 점검에서는 입력 run 안의 외부 대상 symlink를 출력으로 교체할 수 있던 경로도 차단하고 회귀 테스트를 추가했다.
- 최초 built-in 두 세션은 모델/예산 미확인으로 INCONCLUSIVE였다. 이를 보완해 CLI `0.154.0`, `gpt-5.6-luna`, effort `max`, read-only, approval `never`, 사용자 설정 제외, 실행당 180초 한도를 명시하고 **변경 전후 각 2회, 총 4회 새 세션**을 실행했다. 실제 rollout의 model/effort/sandbox와 명령·입력 digest를 대조해 조건을 확인했다. 각 실행의 네 판단과 정책 네 파일의 읽기 기록을 확인했고 최종 evaluator는 **PASS**다. 두 버전 모두 통과했으므로 이 사례에서 회귀가 발견되지 않았다는 결론이며 품질 향상·전면적 삭제 안전성의 증명은 아니다.

## 최종 소비 경로 확인

- 코드 리뷰: `.codex` alias와 기존 `.agents` 호출 이름 모두 같은 source command의 B04로 연결했다.
- handoff: 실제 `~/.codex/skills/handoff`와 `~/.claude/skills/handoff` 링크를 확인했다. Codex의 native `$handoff`로 실제 실행해 vendor 스킬 → 팀 오버라이드 → 증거 계약을 읽는 호출과 파일 SHA-256 재확인을 관찰했다. 이전 PASS의 digest·관찰값과 현재 파일이 다르자 완료 근거 승계를 거부하고 현재 상태 재검증을 다음 행동으로 남겼다.
- 서비스 설치: [설치 안내](service-harness-setup.md#실행-검증-계약-연결), [CLAUDE 양식](../templates/service-harness/CLAUDE.md.tmpl), [AGENTS 양식](../templates/service-harness/AGENTS.md.tmpl), [작업 가이드](harness-guide.md#서비스-하네스-적용-방법)에 계약 준비·실행·등록을 연결했다. 안내의 복사 명령을 임시 repo에서 실행해 최초 생성과 기존 계약 보존을 확인했다.
- completion: 사용되지 않는 YAML `verification_guidance` 키를 제거했다. 실제 [Task Brief 생성기](../tools/generate_discord_orchestrator_payload.py)가 검증 계약 포인터를 전달하며 임시 outbox 파일까지 보존되는 것을 실행 검증했다. 기존 required_fields와 외부 송신 권한은 그대로다.
- 설치 전체 점검: `setup_harness.py --check`는 정상 79건과 기존 전역 설치 경고 54건으로 exit 1이다. 경고는 `eli5-onboard` 전역 링크 누락과 manifest 밖 gstack/orca 스킬이며 pstack 변경 파일의 연결 실패가 아니다. 개인 설치를 reset하거나 제거하지 않았다. 전체 설치 상태까지 무경고라고 보고하지 않는다.
- 스킬 형식: 변경한 legacy alias는 quick_validate 통과. vendor handoff는 원래부터 있는 Claude 전용 `argument-hint`/`disable-model-invocation`을 공용 validator가 허용하지 않아 그 검사에는 실패한다. frontmatter가 이번 변경 전과 동일함을 대조했고 호출 전용 속성을 제거해 통과시키지 않았다.

행동 관찰은 저장된 정책 snapshot의 네 근거 판정에 한정한다. 이후 참조·SoT 등록부의 연결 보완은 별도 소비 경로 검수로 확인했다. 실제 도구의 동작 검증과 문서의 링크·충돌 점검은 최종 파일에 대해 수행했다.

## 적용 범위와 다음 관찰

하네스의 10개 블록과 실행 가능한 검증 사례까지 반영했다. 서비스 앱별 실행 명령·계약 배포는 해당 repo와 환경을 확인하는 별도 작업이다. 확인하지 않은 서비스에 `runtime_contract`나 `verified` 값을 만들지 않았다.

조건 고정과 반복 실행은 이번 최종 검증에서 완료했다. 장기적인 스킬 품질·비용 추세는 실제 요청의 후속 관찰로 축적한다. 현재 도구는 기록된 실행을 비교하며 외부 게시·팀 승인을 자동화하지 않는다.
