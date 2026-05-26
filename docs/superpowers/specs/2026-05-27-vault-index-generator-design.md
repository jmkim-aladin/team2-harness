# vault 인덱스 자동 생성 (Sub 4) 설계

## 배경

Sub 3에서 vault 파일을 새 택소노미로 이관했으나 디렉터리 진입점(`_index.md`)이 부족하다. `services/{aasm,max}/_index.md`, `processes/{capacity,daily,incidents,meetings,tickets}/_index.md` 등이 없어 사람·AI 모두 navigation 어려움.

Sub 4는 vault 내부 navigation `_index.md`를 자동 생성·갱신한다. 데이터 source = vault 디렉터리 listing. harness-link generated block 안 채우기는 Sub 5 별도.

## 원칙

1. **generated block만 자동 갱신** — 사람 작성 본문 보존
2. **dry-run 기본** — `--apply` 명시 실행
3. **vault 디렉터리 listing 기반** — 외부 데이터 의존 없음
4. **기존 _index.md 보존** — 본문 사람 작성 영역은 건드리지 않고 block 안만 교체

## 도구: `harness/tools/generate_vault_indexes.py`

### CLI

```bash
python3 tools/generate_vault_indexes.py \
  --vault "$VAULT" \
  [--target services|processes|hubs|all]   # 기본 all
  [--dry-run | --apply]
  [--log-out <path>]
```

`--target`:
- `services` — `services/{svc}/_index.md`
- `processes` — `processes/{type}/_index.md`
- `hubs` — `wiki/services/_index.md`, `wiki/processes/_index.md`, `wiki/_index.md`(택소노미 entry 갱신만)
- `all` — 위 셋 모두

### 생성 대상

| 파일 | 데이터 source |
|---|---|
| `wiki/services/{svc}/_index.md` | `services/{svc}/{domains|analysis|decisions|proposals|processes}/` 안 `.md` listing |
| `wiki/processes/{type}/_index.md` | `processes/{type}/` 안 `.md` listing (시간순 — filename에 날짜 있으면) |
| `wiki/services/_index.md` | `services/*/` 디렉터리 목록 |
| `wiki/processes/_index.md` | `processes/*/` 카테고리 목록 |

### `_index.md` 구조

신규 생성 시:

```markdown
---
type: service-index | domain-index | process-index | index
title: <한글 제목>
canonical_id: <type>:<slug>
status: canonical
updated_at: YYYY-MM-DD
service_id: <id>        # service-index 일 때만
---

# <한글 제목>

<!-- generated:vault-index source=<rel-path>/ updated=YYYY-MM-DD -->
## <카테고리1>
- [[<file-stem>]]
- ...

## <카테고리2>
- ...
<!-- /generated -->

<!-- generated:harness-link source=team2/catalog/<svc>.yaml updated=N/A -->
(Sub 5에서 채움)
<!-- /generated -->
```

기존 `_index.md` 있으면:
- frontmatter 보존 (updated_at만 갱신)
- 본문 외 generated block만 교체
- harness-link block 부재 시 placeholder 삽입 (Sub 5 진입점)

### 알고리즘

```python
def generate_service_index(vault: Path, svc: str) -> str:
    svc_dir = vault / "wiki/services" / svc
    sub_categories = ["domains", "analysis", "decisions", "proposals", "processes"]
    sections = []
    for cat in sub_categories:
        cat_dir = svc_dir / cat
        if not cat_dir.exists():
            sections.append(f"## {cat}\n- (없음)\n")
            continue
        files = sorted(cat_dir.glob("*.md"))
        if not files:
            sections.append(f"## {cat}\n- (없음)\n")
            continue
        lines = [f"## {cat}"]
        for f in files:
            if f.name == "_index.md":
                continue
            lines.append(f"- [[{f.stem}]]")
        # 하위 디렉터리 (예: domains/{domain}/_index.md)
        for d in sorted(cat_dir.iterdir()):
            if d.is_dir():
                idx = d / "_index.md"
                if idx.exists():
                    lines.append(f"- [[{cat}/{d.name}/_index|{d.name}]]")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)
```

`processes/{type}/_index.md` 도 유사. type별 정렬 키:
- daily, weekly, meetings, tickets → filename 날짜 역순 (최신 위)
- incidents, capacity, okr, sprint → filename 정렬

### `_index.md` 갱신 (재실행 안전)

기존 파일 있으면:
1. 본문 read
2. `<!-- generated:vault-index ... -->` ... `<!-- /generated -->` 블록 정규식 매치
3. 매치되면 그 블록만 교체
4. 매치 안 되고 본문 있으면 surface ("기존 _index에 generated block 없음, 추가 안 함")
5. frontmatter `updated_at` 갱신

### hub _index 생성

`wiki/services/_index.md`:

```markdown
---
type: index
title: 서비스
canonical_id: index:services
status: canonical
updated_at: 2026-05-27
---

# 서비스

<!-- generated:vault-index source=services/ updated=2026-05-27 -->
- [[services/aasm/_index|aasm]]
- [[services/caravan/_index|caravan]]
- [[services/max/_index|max]]
- [[services/shopping/_index|shopping]]
- [[services/tobe/_index|tobe]]
<!-- /generated -->
```

`wiki/processes/_index.md` 동일 패턴.

### dry-run 출력

```
target: all
will create: 7 files (services/{aasm,max}/_index.md, processes/{capacity,daily,...}/_index.md)
will update: 3 files (services/{caravan,shopping,tobe}/_index.md generated block)
will skip: 0 (사람 본문에 generated block 없음 케이스)
```

### Sub 4 산출물

1. `harness/tools/generate_vault_indexes.py`
2. `harness/tools/README.md` 갱신 (generate_vault_indexes 섹션)
3. vault: 신규/갱신된 `_index.md` 다수
4. vault commit

## 비범위

- harness-link generated block 안 채우기 (Sub 5)
- review status 사람 판정 (Sub 2 사람 검토)
- domains/{domain}/_index.md 안 sub-files (별도, 도메인 폴더 안 사람이 작성)
- glossary 자동 생성 (별도)

## 검증

- 모든 `services/*/`, `processes/*/` 안 `_index.md` 존재
- generated block 내 listing == 실제 dir 파일 (현재 시점)
- 기존 _index.md 본문(사람 작성 영역) 손상 0
- frontmatter `updated_at` 갱신됨
- dry-run·apply 정확성 일관
- AI footer 0건
