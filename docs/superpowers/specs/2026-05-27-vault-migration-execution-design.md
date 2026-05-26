# vault 이관 실행 (Sub 3) 설계

## 배경

Sub 2에서 vault 607개 md 파일에 대한 분류표(`vault/wiki/guides/_audit/migration-plan.json`)를 생성했다. Sub 3은 이 분류표를 입력으로 받아 실제 파일 이동·병합·삭제와 wikilink 재작성을 수행한다.

action 분포 (Sub 2 결과):
- move: 128
- merge: 3
- keep: 34
- delete: 3
- review: 439 (사람 검토 후 처리)

Sub 3 도구는 `move/merge/delete` 134건 자동 처리. `keep`는 변경 없음. `review`는 사용자가 분류표에서 dst·action 채워 다시 입력으로 사용하면 다음 실행에서 처리.

## 원칙

1. **단계 분리**: 파일 이관 → wikilink 재작성 → 검증, 세 단계 독립 실행 가능. 부분 진행·중단·재개 안전.
2. **dry-run 기본**: `--apply` 명시 안 하면 실 변경 없이 영향만 출력.
3. **git history 보존**: `git mv` 우선, 실패 시 `mv + git add` fallback.
4. **점진적 commit**: action별·단계별 별도 commit. 한꺼번에 거대 commit 안 함.
5. **자동 merge + surface**: merge 대상 (3건)은 자동 append하되 surface 로그 남겨 사람이 후속 정리.

## 도구: `harness/tools/migrate_vault.py`

### 위치
- `REPO/tools/migrate_vault.py` (신규)
- `REPO/tools/README.md` 갱신 (migrate_vault 섹션 추가)

### CLI

```bash
python3 tools/migrate_vault.py \
  --vault "$VAULT" \
  --plan  "$VAULT/wiki/guides/_audit/migration-plan.json" \
  [--phase 1|2|3|all]              # 기본 all
  [--action move,merge,delete]     # 기본 move,merge,delete
  [--dry-run | --apply]            # 기본 dry-run
  [--log-out "$VAULT/wiki/guides/_audit/migration-log.md"]
```

기본 = `dry-run` (안전). 실 실행은 `--apply` 명시.

### 동작

1. plan.json 로드
2. `--action` 필터로 처리 대상 row만 추림
3. `--phase` 따라 단계 실행:
   - phase 1: 파일 이관 (move/merge/delete)
   - phase 2: wikilink 재작성
   - phase 3: 끊긴 wikilink 검증 + surface
4. migration-log.md 작성 (`--apply` 시)

## 처리 흐름 (Phase 1: 파일 이관)

| action | 처리 |
|---|---|
| `move` | dst 디렉터리 없으면 `mkdir -p`. `git mv src dst` (실패 시 `mv` + `git add`). |
| `merge` | dst 존재: src 본문(frontmatter 이후) 추출 → dst 끝에 `\n\n## (merged from {src_basename})\n\n{body}` append. src `git rm`. surface 로그. dst 미존재: move로 변환. |
| `delete` | `git rm src` (untracked는 `rm`). |
| `keep` | skip. |
| `review` | skip + count 보고. |

각 처리는 vault repo cwd에서. cross-repo 아님.

### git mv vs mv+add fallback

vault `wiki/` 안 다수 파일은 일상 작업물로 untracked일 수 있음. `git mv` 가 untracked 거부 → fallback:

```python
try:
    subprocess.run(["git", "mv", src, dst], check=True, cwd=vault)
except subprocess.CalledProcessError:
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src, dst)
    subprocess.run(["git", "add", dst], check=True, cwd=vault)
```

### merge 처리 상세

```python
def do_merge(vault: Path, src_rel: str, dst_rel: str):
    src = vault / src_rel
    dst = vault / dst_rel
    src_text = src.read_text(encoding="utf-8")
    # frontmatter 제거
    if src_text.startswith("---"):
        end = src_text.find("\n---", 3)
        if end > 0:
            src_text = src_text[end+4:].lstrip("\n")
    if dst.exists():
        dst_text = dst.read_text(encoding="utf-8")
        merged = dst_text.rstrip() + f"\n\n## (merged from {src.name})\n\n" + src_text
        dst.write_text(merged, encoding="utf-8")
        subprocess.run(["git", "add", dst_rel], check=True, cwd=vault)
        subprocess.run(["git", "rm", src_rel], check=True, cwd=vault)
    else:
        # dst 없으면 그냥 move
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", src_rel, dst_rel], check=True, cwd=vault)
```

## 처리 흐름 (Phase 2: wikilink 재작성)

이관 후 옛 경로 가리키는 wikilink 갱신.

### 지원 변형

| 형식 | 예시 |
|---|---|
| 단순 | `[[name]]` |
| 표시명 | `[[name\|display]]` |
| 섹션 | `[[name#section]]` |
| 경로 | `[[path/name]]`, `[[../path/name]]` |

### 알고리즘

```python
# plan.json에서 옛→새 이름 매핑 추출
RENAME = {}
for row in plan:
    if row["action"] not in ("move", "merge"):
        continue
    src = Path(row["src"])
    dst = Path(row["dst"])
    old = src.stem    # 'tobe-content-note-pipeline'
    new = dst.stem    # 'content-note-pipeline' (or 같을 수도)
    if old != new:
        RENAME[old] = new
    # 경로 변형은 별도 처리 (옛 dir → 새 dir)

# 모든 md 본문에 정규식 적용
WIKILINK_RE = re.compile(
    r'\[\[((?:\.\./)*(?:[^/\]|#]+/)*)([^|#\]]+?)(\.md)?(#[^|\]]+)?(\|[^\]]+)?\]\]'
)

def rewrite(text: str) -> str:
    def repl(m: re.Match) -> str:
        path_prefix, name, ext, section, display = m.groups()
        if name in RENAME:
            new_name = RENAME[name]
            # path_prefix 보존 (사용자가 ../path 등 명시한 경우)
            return f"[[{path_prefix or ''}{new_name}{ext or ''}{section or ''}{display or ''}]]"
        return m.group(0)
    return WIKILINK_RE.sub(repl, text)
```

### 충돌 처리

동명 파일 다수 존재 가능 (예: `tobe-foo` → `services/tobe/domains/foo.md`, 다른 곳 `services/shopping/domains/foo.md`도 있을 때). 단순 basename 매치는 잘못 갱신 위험.

대응:
- RENAME 매핑이 service별로 unique한지 사전 검사
- 충돌 시 path_prefix 활용 (예: `[[domains/foo]]` → 어떤 서비스인지 알 수 없음)
- 충돌 surface, 사람 후속 처리

### 실행 흐름

```python
for md_file in vault.rglob("wiki/**/*.md"):
    text = md_file.read_text(encoding="utf-8")
    new_text = rewrite(text)
    if new_text != text:
        md_file.write_text(new_text, encoding="utf-8")
        changed.append(md_file)

subprocess.run(["git", "add", "-A", "wiki/"], cwd=vault)
```

## 처리 흐름 (Phase 3: 검증)

이관 + 재작성 후 잔존 끊긴 wikilink surface.

```python
# 옛 경로/이름이 본문에 남아있는지 검사
for old_name in RENAME.keys():
    matches = subprocess.run(
        ["grep", "-rln", "--include=*.md", f"\\[\\[{old_name}\\]\\]", "wiki/"],
        cwd=vault, capture_output=True, text=True
    )
    if matches.stdout.strip():
        surface[old_name] = matches.stdout.strip().split("\n")
```

surface는 migration-log.md에 기록. 0건 = clean. 잔존 시 사람 후속.

## 산출물: `migration-log.md`

```markdown
---
type: audit-log
title: vault 이관 실행 로그
canonical_id: audit:migration-log
status: canonical
updated_at: 2026-05-27
---

# vault 이관 실행 로그

## 요약

- 입력 plan: {plan_path}
- 실행 시각: 2026-05-27 12:34
- 처리 결과:
  - move: 128 ✓
  - merge: 3 ✓ (surface 항목 N건)
  - delete: 3 ✓
  - keep: 34 (skip)
  - review: 439 (skip)
- wikilink 갱신: M개 파일, K개 링크
- 잔존 끊긴 wikilink: 0 (또는 surface 목록)

## surface (수동 후속 필요)

### merge surface
- {src1.md} → {dst1.md} merge 완료. dst 내용·구조 사람 검토 후 정리 필요.
- ...

### wikilink 충돌
- 동명 파일 여러 곳 — disambiguate 필요
- ...
```

## Sub 3 산출물

1. `REPO/tools/migrate_vault.py` — 이관 도구
2. `REPO/tools/README.md` 갱신 — migrate_vault 섹션
3. `VAULT/wiki/guides/_audit/migration-log.md` — 실행 결과
4. vault commit (이관 + wikilink 재작성, action별 또는 phase별 별도)

## 비범위

- `_index` 자동 생성 (Sub 4)
- harness sync 도구 (Sub 5)
- review 439 row 사람 판정 — 사용자가 plan.json 수동 갱신 후 도구 재실행

## 검증

- `--dry-run` 출력 action별 row 수 == plan.json 통계 일치
- `--apply` 후:
  - vault에서 src 모두 사라짐 (move/merge/delete)
  - dst 모두 생성됨 (move/merge)
  - vault git status에 staged 변경 또는 commit 반영
- wikilink 잔존 검증 = surface 목록 또는 0건
- migration-log.md 작성됨
- AI footer 0건

## 안전장치

- 기본 dry-run, 실 실행은 명시 옵션
- 단계별 분리, 중간 중단 가능
- merge에서 dst 충돌 시 자동 변환 + surface
- 도구 실행 전 vault `git status` 깨끗한 상태 권장 (또는 별도 working branch 분기)
