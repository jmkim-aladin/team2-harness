# harness ↔ vault sync (Sub 5) 설계

## 배경

Sub 4에서 `services/{svc}/_index.md` 등에 `<!-- generated:harness-link -->` 블록 placeholder를 만들었으나 안은 비어 있다. Sub 5는 harness `catalog/*.yaml`, `policies/team-members.md`, `policies/*.md`를 읽어 그 블록 안을 채운다.

원칙: vault는 harness 콘텐츠를 복제하지 않는다. generated block 안에만 자동 갱신되는 참조 표를 둔다. 본문 사람 작성 영역은 보존.

## 도구: `harness/tools/sync_harness_links.py`

stdlib only Python. catalog yaml은 정규식 shallow 파싱 (필요 필드만 추출).

### CLI

```bash
python3 tools/sync_harness_links.py \
  --vault "$VAULT" \
  --harness "$REPO" \
  [--target services|team|policies|all]   # 기본 all
  [--dry-run | --apply]
```

### 갱신 대상

| 파일 | block | 데이터 source |
|---|---|---|
| `services/{svc}/_index.md` | `generated:harness-link` | `harness/catalog/{svc}.yaml` (name, type, status, owners) |
| `processes/team/_index.md` (신규 시 생성) | `generated:team-members` | `harness/policies/team-members.md` 정규직 표 |
| `wiki/_index.md` | `generated:policy-index` | `harness/policies/*.md` 파일 목록 + 1행 요약 |

## catalog yaml shallow 파싱

regex 기반. 추출 필드:
- `service_id`: `^service_id:\s*(\S+)`
- `name`: `^name:\s*(.+)$`
- `type`: `^type:\s*(\S+)`
- `status`: `^status:\s*(\S+)` (있으면)
- `owners.primary`: yaml `owners:` 블록 안 `primary:` 행
- `owners.backup`: 동일
- `owners.additional`, `owners.stakeholders[]`: 동일

미존재 필드는 `None`. 복잡 nested (components, deployment 등)은 skip.

### 이메일 → 한글 이름 매핑

`policies/team-members.md` 첫 번째 표(정규직)에서 `이메일 (YouTrack ID)` 컬럼 추출:
- `jmkim@aladin.co.kr` → `김정민 (jmkim)`
- `heum2@aladin.co.kr` → `조은흠 (heum2)`
- `hyeryun@aladin.co.kr` → `안혜련 (hyeryun)`
- `pms0905@aladin.co.kr` → `박민석 (pms0905)`

프리랜서 표도 동일하게 파싱.

## 블록 형식

### services/{svc}/_index.md

```markdown
<!-- generated:harness-link source=team2/catalog/{svc}.yaml updated=YYYY-MM-DD -->
- 이름: {name}
- 분류: {type} (legacy|new)
- 상태: {status} (있으면)
- 카탈로그: [`catalog/{svc}.yaml`](file://{HARNESS}/catalog/{svc}.yaml)
- 오너: {primary 한글이름} ({primary id}){, 백업: {backup}}{, 추가: {additional/stakeholders 공백 구분}}
<!-- /generated -->
```

### processes/team/_index.md

```markdown
---
type: process-index
title: 팀
canonical_id: process:team
status: canonical
updated_at: YYYY-MM-DD
---

# 팀

<!-- generated:team-members source=team2/policies/team-members.md updated=YYYY-MM-DD -->
| 역할 | 이름 | 담당 서비스 |
|---|---|---|
| 백엔드 개발자 | 김정민 (jmkim) | max, tobe, naru, aasm, caravan, shopping, storefront, blog |
| 백엔드 개발자 | 안혜련 (hyeryun) | storefront |
| 프론트엔드 개발자 | 조은흠 (heum2) | max, tobe, caravan |
| 백엔드 개발자 | 박민석 (pms0905) | (TBD) |
<!-- /generated -->
```

### wiki/_index.md

```markdown
<!-- generated:policy-index source=team2/policies/ updated=YYYY-MM-DD -->
- [`branching-strategy`](file://{HARNESS}/policies/branching-strategy.md) — {1행 요약 또는 H1 다음 첫 문장}
- [`knowledge-base-policy`](file://{HARNESS}/policies/knowledge-base-policy.md) — {요약}
- ...
<!-- /generated -->
```

본문 안 적절 위치에 블록 없으면 신규 삽입, 있으면 안만 교체.

## 처리 흐름

```python
def main():
    parse args
    catalog = parse_catalog_dir(harness/catalog)        # dict[svc → fields]
    name_map = parse_team_members(harness/policies/team-members.md)
                                                          # dict[email → 한글이름 (id)]
    policies = list_policies(harness/policies/)           # list[(name, summary)]

    if target services:
        for svc in catalog:
            update_service_index(vault, svc, catalog[svc], name_map, dry_run)

    if target team:
        update_team_index(vault, name_map, catalog, dry_run)

    if target policies:
        update_policy_index(vault, policies, dry_run)

    report + git add (apply 시)
```

## 신규/기존 처리

| 파일 | 신규 | 기존 (block 있음) | 기존 (block 없음) |
|---|---|---|---|
| `services/{svc}/_index.md` | (Sub 4가 placeholder 만들었어야) skip + surface | 블록 안 교체 | block 삽입 또는 skip |
| `processes/team/_index.md` | 신규 생성 | 블록 안 교체 | 블록 추가 |
| `wiki/_index.md` | (이미 존재) | 블록 안 교체 | 본문 끝에 블록 신규 추가 |

## Sub 5 산출물

1. `harness/tools/sync_harness_links.py`
2. `harness/tools/README.md` 갱신
3. vault: 갱신된 _index.md 다수
4. vault commit + harness commit

## 비범위

- catalog yaml 전체 깊이 파싱 (필요 필드 shallow)
- yaml 형식 변경 시 자동 대응 — 사람이 도구 갱신
- 야간 auto-prep (Sub 6)
- `/ad:*` 스킬 본문 갱신 (Sub 7)

## 검증

- `services/{svc}/_index.md` harness-link 블록 내용 == catalog yaml shallow 추출 일치
- `processes/team/_index.md` team-members 블록 == 정규직 4명 행 (jmkim/heum2/pms0905/hyeryun, 박희수 등 외주 제외 또는 별도 표시)
- `wiki/_index.md` policy-index 블록에 `policies/*.md` 전체 등재
- 사람 본문 영역 변경 0
- AI footer 0건
