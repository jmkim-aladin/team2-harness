#!/bin/bash
# 팀 하네스 초기 셋업 스크립트
# 사용법: ./scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEAM2_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
BACKUP_TS="$(date +%Y%m%d%H%M%S)"

link_path() {
    local src="$1"
    local dest="$2"
    local label="$3"

    mkdir -p "$(dirname "$dest")"

    if [ -L "$dest" ]; then
        if [ "$(readlink "$dest")" = "$src" ]; then
            echo "  이미 연결됨 — $label"
            return
        fi
        echo "  기존 심볼릭 링크 갱신 — $label"
        rm "$dest"
    elif [ -e "$dest" ]; then
        local backup="${dest}.bak-${BACKUP_TS}"
        echo "  기존 항목 백업 — $backup"
        mv "$dest" "$backup"
    fi

    ln -s "$src" "$dest"
    echo "  ✓ $dest → $src"
}

remove_stale_codex_agents() {
    local dest="$CODEX_DIR/AGENTS.md"

    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$TEAM2_DIR/AGENTS.md" ]; then
        echo "  기존 전역 Codex AGENTS 링크 제거 — ~/.codex/AGENTS.md"
        rm "$dest"
    fi
}

link_team2_skills() {
    local dest_root="$1"
    local label="$2"
    local skip_ad="$3"  # skip-ad: Claude Code는 /ad:* command가 있어 ad-* Skill을 중복 연결하지 않음

    mkdir -p "$dest_root"

    if [ -d "$TEAM2_DIR/.codex/skills" ]; then
        for skill_dir in "$TEAM2_DIR"/.codex/skills/*; do
            [ -d "$skill_dir" ] || continue
            local skill_name
            skill_name="$(basename "$skill_dir")"
            if [ "$skip_ad" = "skip-ad" ]; then
                case "$skill_name" in
                ad-*)
                    if [ -L "$dest_root/$skill_name" ]; then
                        echo "  중복 ad Skill 링크 제거 — $label/$skill_name"
                        rm "$dest_root/$skill_name"
                    fi
                    continue
                    ;;
                esac
            fi
            link_path "$skill_dir" "$dest_root/$skill_name" "$label/$skill_name"
        done
    else
        echo "  ⚠ $TEAM2_DIR/.codex/skills 디렉토리가 없습니다."
    fi
}

echo "=== 개발 2팀 하네스 셋업 ==="
echo ""

# 0. TEAM2_HARNESS_PATH 등록
echo "[0/5] 팀 하네스 경로 등록..."

mkdir -p "$CLAUDE_DIR" "$CODEX_DIR"

if [ -f "$CLAUDE_DIR/settings.json" ]; then
    if grep -q "TEAM2_HARNESS_PATH" "$CLAUDE_DIR/settings.json"; then
        echo "  이미 TEAM2_HARNESS_PATH 설정됨 — 경로 갱신합니다."
        # python3으로 JSON 업데이트
        python3 -c "
import json
with open('$CLAUDE_DIR/settings.json', 'r') as f:
    d = json.load(f)
d.setdefault('env', {})['TEAM2_HARNESS_PATH'] = '$TEAM2_DIR'
d['env']['YOUTRACK_BASE_URL'] = 'https://aladincommunication.youtrack.cloud'
with open('$CLAUDE_DIR/settings.json', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
" 2>/dev/null && echo "  ✓ TEAM2_HARNESS_PATH=$TEAM2_DIR" && echo "  ✓ YOUTRACK_BASE_URL 설정됨" || echo "  ⚠ 수동 설정 필요"
    else
        python3 -c "
import json
with open('$CLAUDE_DIR/settings.json', 'r') as f:
    d = json.load(f)
d.setdefault('env', {})['TEAM2_HARNESS_PATH'] = '$TEAM2_DIR'
d['env']['YOUTRACK_BASE_URL'] = 'https://aladincommunication.youtrack.cloud'
with open('$CLAUDE_DIR/settings.json', 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
" 2>/dev/null && echo "  ✓ TEAM2_HARNESS_PATH=$TEAM2_DIR" || echo "  ⚠ 수동 설정 필요"
    fi
else
    echo "  ~/.claude/settings.json 생성..."
    echo "{\"env\":{\"TEAM2_HARNESS_PATH\":\"$TEAM2_DIR\",\"YOUTRACK_BASE_URL\":\"https://aladincommunication.youtrack.cloud\"}}" | python3 -m json.tool > "$CLAUDE_DIR/settings.json"
    echo "  ✓ TEAM2_HARNESS_PATH=$TEAM2_DIR"
    echo "  ✓ YOUTRACK_BASE_URL 설정됨"
fi

# 1. 팀 스킬 심볼릭 링크
echo ""
echo "[1/5] Claude Code /ad 명령 연결..."
mkdir -p "$CLAUDE_DIR/commands"

link_path "$TEAM2_DIR/.claude/commands/ad" "$CLAUDE_DIR/commands/ad" "~/.claude/commands/ad"

# 2. 전역 Codex/Claude Code team2 Skill 연결
echo ""
echo "[2/5] Codex / Claude Code 전역 Skill 연결..."

remove_stale_codex_agents

link_team2_skills "$CODEX_DIR/skills" "~/.codex/skills"
link_team2_skills "$CLAUDE_DIR/skills" "~/.claude/skills" skip-ad

# 3. YouTrack 토큰 확인
echo ""
echo "[3/5] YouTrack 토큰 확인..."

if [ -f "$CLAUDE_DIR/settings.json" ]; then
    if grep -q "YOUTRACK_TOKEN" "$CLAUDE_DIR/settings.json"; then
        echo "  ✓ YOUTRACK_TOKEN 설정됨"
    else
        echo "  ⚠ YOUTRACK_TOKEN이 ~/.claude/settings.json에 없습니다."
        echo ""
        echo "  아래 내용을 ~/.claude/settings.json의 env에 추가하세요:"
        echo '    "YOUTRACK_TOKEN": "perm-XXXX"'
        echo ""
        echo "  토큰 발급: YouTrack > Profile > Account Security > New Token"
    fi
else
    echo "  ⚠ ~/.claude/settings.json이 없습니다."
    echo ""
    echo "  아래 내용으로 ~/.claude/settings.json을 생성하세요:"
    echo '  {'
    echo '    "env": {'
    echo '      "YOUTRACK_TOKEN": "perm-XXXX"'
    echo '    }'
    echo '  }'
fi

# 4. gh CLI 확인
echo ""
echo "[4/5] gh CLI 확인..."

if command -v gh &> /dev/null; then
    echo "  ✓ gh CLI 설치됨: $(gh --version | head -1)"
    if gh auth status &> /dev/null 2>&1; then
        echo "  ✓ gh 인증됨"
    else
        echo "  ⚠ gh 인증 필요: gh auth login"
    fi
else
    echo "  ⚠ gh CLI 미설치"
    echo "  설치: brew install gh"
    echo "  인증: gh auth login"
fi

echo ""
echo "[5/5] 연결 상태 확인..."
if [ -L "$CLAUDE_DIR/commands/ad" ]; then
    echo "  ✓ Claude Code /ad command 연결됨"
else
    echo "  ⚠ Claude Code /ad command 연결 확인 필요"
fi
if [ -L "$CLAUDE_DIR/skills/dev2-team-harness-ko" ] && [ -f "$CLAUDE_DIR/skills/dev2-team-harness-ko/SKILL.md" ]; then
    echo "  ✓ Claude Code team2 Skill 연결됨"
else
    echo "  ⚠ Claude Code team2 Skill 연결 확인 필요"
fi
if [ -L "$CODEX_DIR/skills/ad-ticket" ] && [ -f "$CODEX_DIR/skills/ad-ticket/SKILL.md" ]; then
    echo "  ✓ Codex ad Skill 연결됨"
else
    echo "  ⚠ Codex ad Skill 연결 확인 필요"
fi
if [ -f "$TEAM2_DIR/AGENTS.md" ]; then
    echo "  ✓ Codex repo-local 진입점 확인됨"
else
    echo "  ⚠ Codex repo-local 진입점 확인 필요"
fi

echo ""
echo "ℹ YouTrack은 REST API(YOUTRACK_TOKEN)로만 호출합니다. MCP는 사용하지 않습니다."

echo ""
echo "=== 셋업 완료 ==="
echo ""
echo "사용법:"
echo "  아무 서비스 레포에서 claude 실행 → 팀 스킬 자동 사용 가능"
echo "  /ad:ticket          — 티켓 생성"
echo "  /ad:code-review     — PR 코드 리뷰"
echo "  /ad:architecture-analysis — 저장소 아키텍처 분석 + wiki HTML"
echo "  /ad:team2-kb-read   — KB 문서 조회"
echo "  /ad:team2-kb-list   — KB 문서 목록"
echo "  /ad:team2-kb-sync   — KB → 하네스 동기화"
echo ""
echo "Terminal control pane:"
echo "  export PATH=\"$TEAM2_DIR/bin:\$PATH\""
echo "  team2-agent board"
echo "  team2-agent cockpit"
echo "  team2-agent cycle"
echo "  team2-agent herdr doctor"
echo "  team2-agent herdr install-hooks"
echo "  team2-agent herdr open"
echo "  team2-agent herdr tickets --service max --concurrency 4 DEV2-6509 DEV2-6510"
echo "  team2-agent herdr worker orch-worker-3 \"추가 분석 작업\""
echo "  team2-agent herdr role --service max DEV2-6509 analyst \"요구사항과 코드 진입점 분석\""
echo "  # then type natural-language instructions in the herdr orchestrator pane"
echo ""
echo "Codex:"
echo "  AGENTS.md는 team2 레포의 repo-local 항목을 사용합니다."
echo "  team2 전용 Skill은 ~/.codex/skills, ~/.claude/skills에서 이 레포의 .codex/skills/*로 symlink됩니다."
echo "  단, ad-* Skill은 Claude Code에서 /ad:* command와 중복이므로 ~/.claude/skills에는 연결하지 않습니다."
echo "  Skill 원본은 항상 team2/.codex/skills/*입니다."
echo "  /ad:* 요청은 Skill이 team2/.claude/commands/ad/*.md를 읽고 같은 절차로 수행합니다."
