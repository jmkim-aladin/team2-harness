#!/usr/bin/env python3
"""하네스 컨텍스트·스택·훅 감사.

세 가지를 실측한다:
  1. 상주 컨텍스트 예산 — 세션 시작마다 로드되는 지시문·스킬 description
  2. 스킬 스택 실사용 — 설치 대비 실제 호출 (Claude 슬래시 + Skill 툴 + Codex $alias)
  3. 세션 지표 — 호출당 평균 컨텍스트, 툴 분포, 지연, 반복 Read

임계값을 넘긴 항목은 [경고]로 표시된다. 판정·조치는 사람이 한다.

사용법:
    python3 tools/harness_context_audit.py            # 기본 90일
    python3 tools/harness_context_audit.py --days 30
    python3 tools/harness_context_audit.py --json     # 기계 판독용
"""
import argparse, glob, json, os, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~")
HARNESS = os.environ.get("TEAM2_HARNESS_PATH", os.path.join(HOME, "Documents/workspace/team2"))
CLAUDE_DIR = os.path.join(HOME, ".claude")

# 임계값 — 넘으면 경고. 근거는 docs/skill-stack-and-workflow-plan.md §1
LIMITS = {
    "resident_tokens": 8000,      # 상주 컨텍스트
    "avg_context_tokens": 200000, # 호출당 평균 컨텍스트 (smart zone 약 150k)
    "bash_share": 0.50,           # Bash가 전체 툴 호출에서 차지하는 비중
    "cd_share": 0.20,             # Bash 중 cd 비율
    "reread_count": 5,            # 같은 파일 재독 횟수
}


def read(p):
    try:
        with open(p, errors="ignore") as f: return f.read()
    except Exception: return ""


def frontmatter(text):
    m = re.search(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def description_cost(path):
    """모델 컨텍스트에 상주하는 description 길이. 사용자 호출 전용이면 0."""
    fm = frontmatter(read(path))
    if not fm: return 0
    if "disable-model-invocation: true" in fm: return 0
    d = re.search(r"^description:\s*(.*(?:\n[ \t]+.*)*)", fm, re.M)
    return len(d.group(1)) if d else 0


def resident_budget():
    rows = []
    for label, p in (
        ("harness CLAUDE.md", os.path.join(HARNESS, "CLAUDE.md")),
        ("harness AGENTS.md", os.path.join(HARNESS, "AGENTS.md")),
    ):
        rows.append((label, len(read(p))))
    personal = sum(len(read(os.path.join(CLAUDE_DIR, f)))
                   for f in os.listdir(CLAUDE_DIR)
                   if f.endswith(".md") and os.path.isfile(os.path.join(CLAUDE_DIR, f)))
    rows.append(("~/.claude 메모리(*.md)", personal))

    skills_dir = os.path.join(CLAUDE_DIR, "skills")
    if os.path.isdir(skills_dir):
        rows.append(("설치 스킬 description",
                     sum(description_cost(os.path.join(skills_dir, d, "SKILL.md"))
                         for d in os.listdir(skills_dir))))
    cmd_dir = os.path.join(HARNESS, ".claude/commands/ad")
    if os.path.isdir(cmd_dir):
        rows.append(("ad:* description",
                     sum(description_cost(os.path.join(cmd_dir, f))
                         for f in os.listdir(cmd_dir) if f.endswith(".md"))))
    # 활성 플러그인만 — 비활성/구버전 캐시는 컨텍스트에 로드되지 않는다
    settings = json.loads(read(os.path.join(CLAUDE_DIR, "settings.json")) or "{}")
    enabled = {k for k, v in (settings.get("enabledPlugins") or {}).items() if v}
    installed = json.loads(read(os.path.join(CLAUDE_DIR, "plugins/installed_plugins.json")) or "{}")
    for key, entries in (installed.get("plugins") or {}).items():
        if key not in enabled: continue
        for e in entries:
            sp = os.path.join(e.get("installPath", ""), "skills")
            if not os.path.isdir(sp): continue
            rows.append((f"플러그인 {key.split('@')[0]} description",
                         sum(description_cost(os.path.join(sp, d, "SKILL.md")) for d in os.listdir(sp))))
    return rows


def hooks():
    s = json.loads(read(os.path.join(CLAUDE_DIR, "settings.json")) or "{}")
    out = []
    for ev, groups in (s.get("hooks") or {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                out.append((ev, g.get("matcher", "(all)"), h.get("command", "")[:80]))
    return out


def sessions(days):
    cut = datetime.now(timezone.utc) - timedelta(days=days)
    skill_hits, last = Counter(), {}
    tool_calls, tool_result_chars, tool_errors = Counter(), Counter(), Counter()
    tool_latency = defaultdict(list)
    reads, bash_head = Counter(), Counter()
    tok = Counter()
    cmd_re = re.compile(r"<command-name>/?([^<]+)</command-name>")
    pending = {}

    def stamp(rec):
        t = rec.get("timestamp")
        if not t: return None
        try: return datetime.fromisoformat(t.replace("Z", "+00:00"))
        except Exception: return None

    for path in glob.glob(os.path.join(CLAUDE_DIR, "projects/**/*.jsonl"), recursive=True):
        try: fh = open(path, errors="ignore")
        except Exception: continue
        with fh:
            for line in fh:
                try: rec = json.loads(line)
                except Exception: continue
                t = stamp(rec)
                if not t or t < cut: continue
                day = t.strftime("%Y-%m-%d")
                msg = rec.get("message") or {}
                for k in ("input_tokens", "output_tokens",
                          "cache_read_input_tokens", "cache_creation_input_tokens"):
                    tok[k] += (msg.get("usage") or {}).get(k) or 0
                content = msg.get("content")
                items = content if isinstance(content, list) else (
                    [{"type": "text", "text": content}] if isinstance(content, str) else [])
                for c in items:
                    if not isinstance(c, dict): continue
                    if c.get("type") == "text":
                        for m in cmd_re.findall(c.get("text") or ""):
                            n = m.strip().split()[0].lstrip("/")
                            skill_hits[n] += 1; last[n] = max(last.get(n, ""), day)
                    elif c.get("type") == "tool_use":
                        name = c.get("name") or "?"
                        tool_calls[name] += 1
                        pending[c.get("id")] = (name, t)
                        inp = c.get("input") or {}
                        if name == "Skill" and inp.get("skill"):
                            s = inp["skill"]; skill_hits[s] += 1; last[s] = max(last.get(s, ""), day)
                        elif name == "Read" and inp.get("file_path"):
                            reads[inp["file_path"]] += 1
                        elif name == "Bash":
                            parts = (inp.get("command") or "").strip().split()
                            if parts: bash_head[parts[0]] += 1
                    elif c.get("type") == "tool_result":
                        name, t0 = pending.pop(c.get("tool_use_id"), (None, None))
                        body = c.get("content")
                        s = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
                        if name:
                            tool_result_chars[name] += len(s)
                            if t0: tool_latency[name].append((t - t0).total_seconds())
                        if c.get("is_error"): tool_errors[name or "?"] += 1

    # Codex $alias
    for path in glob.glob(os.path.join(HOME, ".codex/sessions/**/*.jsonl"), recursive=True):
        for m in re.findall(r"(?:^|\s)\$([a-z0-9_-]+)", read(path)):
            skill_hits[m] += 1
    return dict(skill_hits=skill_hits, last=last, tool_calls=tool_calls,
                tool_result_chars=tool_result_chars, tool_errors=tool_errors,
                tool_latency=tool_latency, reads=reads, bash_head=bash_head, tok=tok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    budget = resident_budget()
    resident_chars = sum(c for _, c in budget)
    resident_tok = resident_chars // 4
    hk = hooks()
    S = sessions(a.days)

    calls = sum(S["tool_calls"].values())
    cache_read = S["tok"]["cache_read_input_tokens"]
    avg_ctx = cache_read // calls if calls else 0
    bash = S["tool_calls"].get("Bash", 0)
    bash_share = bash / calls if calls else 0
    cd_share = S["bash_head"].get("cd", 0) / bash if bash else 0

    warn = []
    if resident_tok > LIMITS["resident_tokens"]: warn.append(f"상주 컨텍스트 {resident_tok:,} tok > {LIMITS['resident_tokens']:,}")
    if avg_ctx > LIMITS["avg_context_tokens"]: warn.append(f"호출당 평균 컨텍스트 {avg_ctx:,} tok > {LIMITS['avg_context_tokens']:,} (smart zone 이탈)")
    if bash_share > LIMITS["bash_share"]: warn.append(f"Bash 비중 {bash_share:.0%} > {LIMITS['bash_share']:.0%} (파일은 Read로)")
    if cd_share > LIMITS["cd_share"]: warn.append(f"Bash 중 cd {cd_share:.0%} > {LIMITS['cd_share']:.0%} (절대 경로 사용)")

    if a.json:
        print(json.dumps({
            "days": a.days, "resident_tokens": resident_tok,
            "resident_breakdown": {n: c for n, c in budget},
            "hooks": [{"event": e, "matcher": m, "command": c} for e, m, c in hk],
            "avg_context_tokens": avg_ctx, "tool_calls": dict(S["tool_calls"]),
            "bash_share": round(bash_share, 3), "cd_share": round(cd_share, 3),
            "skill_hits": dict(S["skill_hits"]), "warnings": warn,
        }, ensure_ascii=False, indent=2))
        return

    print(f"===== 하네스 컨텍스트 감사 (최근 {a.days}일) =====\n")

    print("## 1. 상주 컨텍스트 예산")
    for n, c in budget: print(f"  {n:<34}{c:>8,} chars {c//4:>7,} tok")
    print(f"  {'합계':<34}{resident_chars:>8,} chars {resident_tok:>7,} tok")
    print()

    print("## 2. 훅")
    if not hk: print("  없음")
    for e, m, c in hk: print(f"  {e:<18}{m:<34}{c}")
    print()

    print("## 3. 세션 지표")
    print(f"  툴 호출              {calls:,}")
    print(f"  캐시 읽기            {cache_read/1e6:,.0f}M tok")
    print(f"  출력                 {S['tok']['output_tokens']/1e6:,.1f}M tok")
    print(f"  호출당 평균 컨텍스트   {avg_ctx:,} tok   (smart zone 약 150,000)")
    print(f"  Bash 비중            {bash_share:.1%}   (Bash 중 cd {cd_share:.1%})")
    print()

    print("## 4. 툴 분포·지연")
    print(f"  {'툴':<20}{'호출':>7}{'중앙값s':>9}{'총초':>9}{'결과chars':>13}{'오류':>6}")
    for n, c in S["tool_calls"].most_common(12):
        lat = sorted(S["tool_latency"].get(n, []))
        med = lat[len(lat)//2] if lat else 0
        print(f"  {n:<20}{c:>7}{med:>9.2f}{sum(lat):>9.0f}{S['tool_result_chars'][n]:>13,}{S['tool_errors'][n]:>6}")
    print()

    print(f"## 5. 반복 Read ({LIMITS['reread_count']}회 초과)")
    for f, c in S["reads"].most_common(15):
        if c > LIMITS["reread_count"]: print(f"  {c:>4}  {f}")
    print()

    print("## 6. 설치 스킬 실사용")
    skills_dir = os.path.join(CLAUDE_DIR, "skills")
    cmd_dir = os.path.join(HARNESS, ".claude/commands/ad")
    installed = []
    if os.path.isdir(skills_dir):
        installed += [(d, d) for d in sorted(os.listdir(skills_dir))]
    if os.path.isdir(cmd_dir):
        installed += [(f"ad:{f[:-3]}", f"ad-{f[:-3]}") for f in sorted(os.listdir(cmd_dir)) if f.endswith(".md")]
    unused = []
    for label, alias in installed:
        n = S["skill_hits"].get(label, 0) + S["skill_hits"].get(alias, 0)
        if n: print(f"  {n:>5}  {label:<28} last={S['last'].get(label, '-')}")
        else: unused.append(label)
    print(f"\n  미사용 {len(unused)}종: " + " ".join(unused))
    print()

    print("## 판정")
    if warn:
        for w in warn: print(f"  [경고] {w}")
    else:
        print("  임계값 초과 없음")
    print("\n  조치는 사람이 판정한다. 0회 스킬은 Codex·Hermes cron 경로를 확인한 뒤 비활성 제안.")


if __name__ == "__main__":
    main()
