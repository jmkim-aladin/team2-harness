# 릴리스 묶음 PR 리뷰

[`/ad:code-review`](../../.claude/commands/ad/code-review.md) 1단계에서 base가 `deploy/*`·`master`·`main`·`release/{YYYY.M.N}`이고 `--full`이 없을 때 읽는다. stage·prod 배포 PR은 대개 이미 리뷰·해소된 작업을 모은 것이라, 전체를 첫 리뷰처럼 재판정하면 해소된 논의를 되살리고 **묶으면서 생기는 문제**(빠진 커밋, 릴리스에서만 바뀐 줄, 기능 간 충돌, 환경값, 배포 순서)를 놓친다. 근거: 2026-09-23 Tobe PR #209(`release/v2026.9.1 → deploy/prod-tobe-web`, 14커밋) — 500줄을 전체 재판정했고 교차 모델엔 잘린 diff가 갔으며 원 PR 리뷰 상태와 base 비머지 커밋 4개를 보지 않았다.

## 판별 — 브랜치 이름이 아니라 원 PR 증거로

레포마다 직배포(`feature/* → main`)와 통합 브랜치 경유(`stage → main`, `dev → main`, `release/* → deploy/*`)가 섞여 있고 head 이름도 제각각이다.

- **원 PR** = 커밋에서 추적된 PR 중 이번 PR(#N)이 아니고, `merged_at`이 있고, `base.ref`가 이번 PR의 base와 다른 것 — 이 셋을 걸러야 트렁크 레포의 feature PR이 자기 자신을 원 PR로 잡지 않는다
- **원 PR 1개 이상** → 묶음 모드. 일부 커밋만 추적되면 묶음 모드로 가되 추적 안 된 커밋은 **릴리스 전용 변경**으로 일반 판정한다
- **원 PR 0개** → 일반 리뷰. base가 `main`·`master`면 직배포 여부를 본다: `gh pr list --repo {owner}/{repo} --base {base} --state merged --limit 10 --json headRefName`에서 최근 머지 대부분이 기능 브랜치면 직배포 레포다. 그러면 운영 축을 조건과 무관하게 적용하고(롤백 경로·설정값·마이그레이션 순서) 미리보기에 `배포 경로: {base} 직배포 — 근거 최근 머지 {N}건 중 기능 브랜치 {N}`을 노출한다. 판단이 안 서면 `확인 못 한 것`에 적는다

실측 2026-09-23: DrmBatchServer #16(`feature/T1-… → main`, 원 PR 0) 일반·직배포 / aladin-mall-migration #758(`stage → main`, #746~#757) 묶음 / backoffice-db-api #691(`dev → main`, #690) 묶음.

## 원 PR 추적

```bash
# 커밋 SHA · 제목 · cherry-pick 원 SHA
gh api repos/{owner}/{repo}/pulls/{N}/commits --paginate \
  --jq '.[] | [.sha, (.commit.message|split("\n")[0]), ((.commit.message|capture("cherry picked from commit (?<s>[0-9a-f]{40})")|.s) // "")] | @tsv'

# 원 SHA(없으면 커밋 SHA) → 원 PR. "Merge pull request #M" 커밋은 제목의 #M을 쓴다
gh api repos/{owner}/{repo}/commits/{sha}/pulls \
  --jq '.[] | select(.number != {N} and .merged_at != null and .base.ref != "{baseRefName}") | "\(.number) \(.base.ref) \(.merged_at)"'

# 원 PR의 리뷰 상태와 [중요] 코멘트
gh api repos/{owner}/{repo}/pulls/{M}/reviews --jq '[.[].state] | unique'
gh api repos/{owner}/{repo}/pulls/{M}/comments --jq '.[] | select(.body|startswith("**[중요]")) | "\(.id) \(.path):\(.line) reply_to=\(.in_reply_to_id)"'
```

- **리뷰됨** = 원 PR에 `APPROVED`가 1개 이상. 원 PR이 없거나 미승인이면 그 커밋의 변경은 일반 리뷰 대상이다
- **통합 브랜치** = 원 PR들의 `base.ref` 중 가장 많은 것(보통 `develop`, 서비스에 따라 `deploy/stg-*`). 하드코딩하지 않는다 — 서비스마다 다르다

## 재판정 범위 좁히기

diff의 파일마다 릴리스 head와 통합 브랜치의 blob을 비교하고, 다르면 두 원본을 `rtk proxy`로 받아 `diff -u` 한다.

```bash
gh api "repos/{owner}/{repo}/contents/{path}?ref={headRefOid}" --jq .sha   # 통합 브랜치 ref로 한 번 더
```

| 결과 | 처리 |
|---|---|
| blob 동일, 관련 원 PR 전부 리뷰됨 | 재판정하지 않는다 — 이해 패스엔 원 PR 번호만 남긴다 |
| 릴리스 쪽에만 있는 줄 | 릴리스 전용 변경(충돌 해소·부분 cherry-pick·직접 수정) — 일반 리뷰 기준으로 판정 |
| 통합 브랜치 쪽에만 있는 줄 | 통합 브랜치가 앞서 갔거나 누락. 그 줄의 커밋이 이번 묶음의 원 PR에 속하면 누락이다 |

## 묶음 검토 축

원래 diff hunk 밖이어도 묶음 구성 자체가 판정 대상이다(본문 §리뷰 범위의 예외). 기준·스펙·운영 축과 따로 보고한다.

| 항목 | 확인 | 판정 |
|---|---|---|
| 누락 | 원 PR 커밋 목록(`pulls/{M}/commits`)과 묶음의 cherry-pick 원 SHA 대조. 특히 `코드리뷰 수정`·후속 fix | 빠진 커밋이 원 PR 리뷰 지적을 해소한 것이면 `[중요]` |
| 혼입 | PR 본문·티켓 목록에 없는 커밋 | `[질문]` — 의도된 동봉인지 |
| 교차 영향 | 서로 다른 원 PR이 같은 파일·전역(설정 키·전역 변수·공유 state·SP)을 건드리는지 — 합쳐진 상태는 아무도 보지 않았다 | 겹치면 그 지점을 릴리스 전용 변경처럼 판정 |
| 환경값 | base 환경(prod/stg)의 transform·설정 값이 그 환경 것인지, dev·stg 호스트·테스트 ID·디버그 플래그 잔존 | 틀리면 `[중요]` |
| 선행 의존 | 참조하는 심볼·SP·설정 키·타 서비스 배포가 묶음이나 base에 있는지 | 없으면 `[중요]`. 레포 밖(SP·타 서비스)이면 `확인 못 한 것` + 배포 순서 질의 |
| 원 PR 미해소 | 원 PR `[중요]` 코멘트 중 답글·후속 커밋이 없는 것 | 스레드 링크와 함께 `[질문]` |
| base 드리프트 | `gh api repos/{owner}/{repo}/compare/{headRefOid}...{baseRefOid}`로 base에만 있는 커밋. 머지 커밋(부모 2개)은 이전 릴리스라 정상, 비머지(운영 직접 수정·hotfix)가 묶음 파일과 겹치는지 | 겹치면 `[질문]` — 덮이거나 충돌 해소가 필요한지 |

- compare는 브랜치 이름이 아니라 `baseRefOid`/`headRefOid`로 한다 — 머지 후 ref가 움직인다 (2026-09-23 Tobe #209 머지 후: 이름 기준 `ahead 0 / behind 14`, SHA 기준 `ahead 14 / behind 13`)
- 롤백 단위: 한 기능만 되돌릴 때 커밋·설정·SP가 분리돼 있는지를 운영 축 근거로 적는다

## 교차 검증

재판정 대상만 보낸다 — 릴리스 전용 변경 hunk, 교차 영향 지점, 미리뷰 원 PR의 hunk. 이미 리뷰된 hunk까지 보내면 diff가 잘려 재판정 대상이 묻힌다 (Tobe #209: 919줄 전체를 보내 codex가 도구 출력 잘림으로 일부를 못 봤다). 재판정 대상이 0이면 `교차검증: 생략 — 묶음 재판정 대상 0`으로 적는다 — 승인 조건 충족은 원 PR 교차검증 근거가 있을 때만이다(본문 §이벤트와 승인 조건). 위험 신호는 재판정 대상 안에서만 센다 — 이미 리뷰된 hunk는 원 PR의 몫이다.

## 미리보기 추가분

리뷰 결과 헤더에 한 줄, 그 아래 묶음 검토 블록을 둔다.

````markdown
묶음: 원 PR {N}개 — 리뷰됨 {N} / 미리뷰 {N} · 재판정 파일 {N}/{전체}

### 묶음 검토
| 원 PR | 티켓 | 리뷰 | 파일 | 재판정 |
|---|---|---|---|---|
| #{M} | {이슈ID} | APPROVED / 미승인 / 원 PR 없음 | {N}개 | 없음 / 릴리스 전용 {N}줄 |

✅ 누락: {원 PR 커밋 대조 결과} · ⚠️ 교차 영향: {겹치는 파일·전역} · ❓ 선행 의존: {레포 밖 SP·배포} · ✅ 환경값 · ✅ base 드리프트: 비머지 {N}개, 겹침 {N}
````
