# vault 파일 감사·분류 매트릭스 (Sub 2) 설계

## 배경

`2026-05-27-vault-taxonomy-design.md`(Sub 1)에서 정의한 새 vault 택소노미에 기존 607개 md 파일을 대응시켜야 한다. Sub 2는 *분류 매트릭스 산출*만 다루고, 실제 파일 이동·wikilink 재작성은 Sub 3에서 수행한다.

현재 vault `wiki/` 디렉터리 분포 (Sub 1.5 cleanup 직후):

```
188 guides       148 contracts   62 inventory    53 projects
35 tickets       24 execution    14 proposals    12 domains
12 daily         10 okr          7 glossary      5 tasks
5 imports        5 decisions     4 services      4 processes
3 usecases       3 meetings      3 indexes       3 briefs
2 templates      2 incidents     1 capacity      0 patterns
0 exports        0 archive
```

총 607 md. 서비스 prefix 패턴 (tobe-, web-aladin- 등) 다수.

## 원칙

1. **하이브리드**: 룰 기반 자동 분류 1차 → 사람 검토 2차. 자동 결정은 confidence high 룰만, 애매한 건 `action=review`로 surface.
2. **결정은 매트릭스에**: Sub 2는 위치 결정만. 실제 이동은 Sub 3.
3. **도구는 harness**: 분류 도구는 harness `tools/`에 둠. vault는 운영 지식만.
4. **이관 후 깨진 wikilink는 Sub 3에서 일괄 처리** — Sub 2 산출물엔 위치만, link 재작성은 Sub 3 grep+replace.

## 서비스 매핑

| prefix (filename 또는 dir) | service_id (catalog) |
|---|---|
| `tobe` | tobe |
| `web`, `web-aladin` | shopping (알라딘 쇼핑 메인 웹 동의어) |
| `max` | max |
| `aasm` | aasm |
| `shopping` | shopping |
| `caravan` | caravan |
| `naru` | naru |
| `bazaar` | bazaar |
| `storefront`, `b2b-store` | storefront |
| `blog`, `bookple` | blog |

매핑 안 되는 prefix → `service=unknown`, action=`review`.

## 분류 룰

현재 dir + filename pattern → 새 위치 + action.

| 현 dir | filename pattern | 새 위치 템플릿 | action |
|---|---|---|---|
| `daily/` | `*` | `processes/daily/{name}` | move |
| `meetings/` | `*` | `processes/meetings/{name}` | move |
| `okr/` | `*` | `processes/okr/{name}` (이미 위치) | keep |
| `tickets/` | `dev2-\d+.md` | `processes/tickets/{status_from_fm 또는 in-progress 기본}/{name}` | move |
| `incidents/` | `*` | `processes/incidents/{name}` | move |
| `capacity/` | `*` | `processes/capacity/{name}` | move |
| `briefs/` | `*` | (사람 판정) | review |
| `execution/` | `*` | `processes/sprint/{name}` 또는 `services/{svc}/processes/` | review |
| `indexes/` | `*` | DELETE (Sub 4에서 자동 재생성) | delete |
| `archive/`, `exports/`, `patterns/`, `imports/`, `templates/` | `*` | DELETE 또는 `guides/` (사람 판정) | review |
| `contracts/{type}/{svc}/` | `*` | `services/{svc}/analysis/{name}` 또는 DELETE (raw enumeration일 때) | review |
| `inventory/` | `{svc}-*` | `services/{svc}/analysis/{name}` | move |
| `domains/` | `{svc}-*` | `services/{svc}/domains/{name}` | move |
| `proposals/` | `{svc}-*` | `services/{svc}/proposals/{name}` | move |
| `decisions/` | `{svc}-*` | `services/{svc}/decisions/{name}` | move |
| `guides/` | `{svc}-*` | `services/{svc}/processes/` 또는 `services/{svc}/domains/` (사람 판정) | review |
| `guides/` | 메타 (`taxonomy.md`, `frontmatter-spec.md`, `document-placement.md`, `skills-integration.md`, `harness-link-protocol.md`, `lint-*`, `ai-human-readable-structure.md` 등) | `guides/{name}` (잔류) | keep |
| `services/` (단일 .md) | `{svc}.md` | `services/{svc}/_index.md` (병합) | merge |
| `tasks/`, `usecases/` | `*` | `processes/tickets/` 또는 `services/{svc}/proposals/` (사람 판정) | review |
| `projects/` | `*` | `projects/{name}` (구조 점검 후 결정) | review |
| `glossary/` | `*` | `glossary/{name}` (잔류) | keep |
| `processes/` (vault wiki 안 기존 4건) | `*` | service-specific은 `services/{svc}/processes/`, ops-level은 `processes/` (사람 판정) | review |

confidence:
- **high**: dir + prefix 둘 다 명확 매치
- **medium**: dir만 매치 또는 prefix만 매치
- **low**: 매칭 모호 — 보통 review로

## 도구: `harness/tools/audit_vault.py`

### 파일 위치
- `REPO/tools/audit_vault.py` (신규)
- `REPO/tools/README.md` (도구 사용법)

vault 안에 두지 않음. 도구는 repo SoT.

### CLI

```bash
python3 tools/audit_vault.py \
  --vault "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2" \
  --catalog catalog/ \
  --output-md "<vault>/wiki/guides/_audit/migration-plan.md" \
  --output-json "<vault>/wiki/guides/_audit/migration-plan.json"
```

### 동작

1. `find {vault}/wiki -type f -name '*.md'` — 모든 md 수집 (단, `wiki/guides/_audit/` 자기 제외)
2. 각 파일 metadata 추출:
   - 현 경로 (relative to vault)
   - 현 dir (top-level wiki subdir)
   - filename (without ext)
   - frontmatter 파싱 (있으면)
3. 룰 적용:
   - service prefix 매치 → service_id 결정
   - dir + 룰 → 새 위치 템플릿 + action
   - confidence 계산
4. 출력 (md + json)

### 매핑 안 되는 경우

- prefix 매치 실패 → `service=unknown`
- 룰 매치 실패 → `action=review`, `dst="(사람 판정 필요)"`

## 산출물

### `vault/wiki/guides/_audit/migration-plan.md`

표 구조 (서비스별 섹션 + 정렬: action=delete → review → merge → keep → move):

```markdown
---
type: audit-report
title: vault 마이그레이션 분류표
canonical_id: audit:vault-migration-plan
status: draft
updated_at: 2026-05-27
---

# vault 마이그레이션 분류표

총 607개 파일. 도구: `harness/tools/audit_vault.py`. 룰 기반 자동 분류 1차. `action=review` row는 사람 검토 후 확정.

## 요약

| service | total | move | merge | keep | delete | review |
|---|---:|---:|---:|---:|---:|---:|
| tobe | 250 | 200 | 1 | 0 | 5 | 44 |
| shopping | 80 | 60 | 1 | 0 | 3 | 16 |
| ... | ... |

## tobe

| 현 경로 | 제안 경로 | action | confidence | 메모 |
|---|---|---|---|---|
| wiki/domains/tobe-content-note-pipeline.md | services/tobe/domains/content-note-pipeline.md | move | high | dir=domains, prefix=tobe |
| ...

## shopping

| ... |

## unknown / review

| ... |

## guides (잔류)

| ... |

## delete 대상

| ... |
```

### `vault/wiki/guides/_audit/migration-plan.json`

```json
[
  {
    "src": "wiki/domains/tobe-content-note-pipeline.md",
    "dst": "services/tobe/domains/content-note-pipeline.md",
    "action": "move",
    "confidence": "high",
    "service": "tobe",
    "category": "domains",
    "reason": "dir=domains, prefix=tobe-"
  },
  {
    "src": "wiki/briefs/sample.md",
    "dst": null,
    "action": "review",
    "confidence": "low",
    "service": null,
    "category": null,
    "reason": "briefs/ 디렉터리, 룰 매치 안 됨"
  }
]
```

## 수동 검토 게이트

1. 자동 분류 실행 → md + json 생성
2. **사용자가 md 직접 편집** — `action=review` row의 `제안 경로`, `action` 컬럼 채움
3. `audit_vault.py --resync-json` 으로 편집된 md를 다시 파싱해 json 재생성
4. `action=review` row 0 = 완료

검토 분할 가능 — 서비스별, 카테고리별로 나눠 진행. 부분 완료 시 commit 가능.

## 깨진 참조 처리 정책

Sub 2는 위치 결정만. 이관 후 wikilink 깨짐은 Sub 3에서 일괄 grep+sed로 처리.

Sub 3 grep+replace는 다음 변형 모두 지원해야:
- `[[name]]`
- `[[name|display text]]`
- `[[name#section]]`
- `[[path/name]]`
- `[[../path/name]]`

Sub 2 산출물에서는 link 변경 영향만 surface (옵션): `audit_vault.py --analyze-backlinks` 로 이관 영향 받는 wikilink 수 보고.

## Sub 2 산출물 목록

1. `REPO/tools/audit_vault.py` — 분류 도구 (Python 단일 파일, stdlib only)
2. `REPO/tools/README.md` — 도구 사용법 + 검토 절차
3. `VAULT/wiki/guides/_audit/migration-plan.md` — 분류 결과 markdown
4. `VAULT/wiki/guides/_audit/migration-plan.json` — 분류 결과 json

## 비범위

- 실제 파일 이동 (Sub 3)
- wikilink 재작성 (Sub 3)
- `_index` 재생성 (Sub 4)
- harness sync 도구 (Sub 5)

## 검증

- `migration-plan.json` row 수 == `find vault/wiki -name '*.md' | wc -l` (감사 도구 자기 제외)
- 모든 row에 `src`, `action`, `confidence` 채워짐
- `action=move` row의 `dst`가 새 택소노미 (`processes/`, `services/{id}/`, `projects/`, `guides/`, `glossary/`) prefix 매치
- 수동 검토 완료 시 `action=review` row 0
- `service` 컬럼 값이 catalog service_id 목록 ∪ {unknown}에 들어감
