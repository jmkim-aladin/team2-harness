# 하네스 변경 요약 — 2026-08 정비 (팀 공유용)

> 스프린트 회의 공유 자료. 상세 근거: [docs/skill-stack-and-workflow-plan.md](./skill-stack-and-workflow-plan.md) · 회차 기록: [docs/skill-audit-baseline.md](./skill-audit-baseline.md) 3회차

## 무엇이 바뀌었나 (PR #6~#21)

1. **작업 플로우가 생겼다** — 상황당 동사 하나. 메인: `/ad:grill`(정렬 인터뷰) → `/ad:ticket` → `/ad:work-prep` → `/ad:implement`(TDD) → `/ad:code-review` → `/ad:work-close`. 신설: `/ad:grill`·`/ad:implement`·`/ad:plan`(위키 계획 노트). 전체 지도: [docs/harness-guide.md](./harness-guide.md) §작업 플로우
2. **외부 스킬 정리** — GSD·superpowers 제거(mattpocock/skills 15→17종이 대체, repo `vendor/`에 버전 고정), gstack은 실사용분만. 스킬 79→21종, 상주 컨텍스트 ~1/3 감소
3. **환경이 선언형이 됐다** — `harness.manifest.json`이 SoT, `python3 tools/setup_harness.py`로 어떤 머신이든 수렴 (Mac/Windows·Claude/Codex 공통)
4. **자격증명 규칙** — 토큰·DB 암호는 OS 금고(mac Keychain / win Credential Manager)에만. 평문 파일 금지, `tools/secret_scan.py`가 감시
5. **문서 전 계층 감사·정비** — 스킬 22종 + 정책·템플릿·가이드 77파일. "반드시"는 진짜 게이트에만 남고, 중복·드리프트 제거. 서비스 카탈로그에 **검증 루프**(빌드·테스트 명령 실증) 등재
6. **용어집 가동** — vault `wiki/glossary/` (한국어 alias로 `[[적립금]]`처럼 링크). 방향 원칙: [policies/harness-north-star.md](../policies/harness-north-star.md)

## 각자 할 일 (1회, ~10분)

```bash
cd ~/Documents/workspace/team2 && git pull
python3 tools/setup_harness.py          # 링크·env 수렴 (몇 번 돌려도 안전)
python3 tools/cred.py set youtrack-token   # 본인 YouTrack 토큰 (프롬프트 입력)
python3 tools/cred.py set cool-dev         # dev DB (기존 Keychain 있으면 생략)
python3 tools/cred.py check                # 확인
```

Windows: 사전에 `pip install keyring` 1회. 문제 시 `python3 tools/setup_harness.py --check` 결과를 공유.

## 리뷰 규칙 (신설)

**정책·INVARIANT 변경 PR은 팀원 1인 리뷰 필수.** 그 외 하네스 PR은 셀프 머지 허용 + 이 문서·회의로 사후 공유. 판별: `policies/instruction-precedence-policy.md`의 invariant/policy 등급을 바꾸거나 신설하는 변경. (근거: 2026-08 정비 21건이 전부 셀프 머지 — 거버넌스 "판정은 사람"의 사람이 1인이었던 구조 보완, 2026-08-09 확정)

## 질문·이상 동작

`/ad:harness-optimize` 실행 결과와 함께 공유. 되돌리기: 모든 비활성은 `~/.claude/harness-quarantine-*` 이동 방식이라 `mv`로 복원 가능.
