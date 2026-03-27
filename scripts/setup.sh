#!/bin/bash
# 팀 하네스 초기 셋업 스크립트
# 사용법: ./scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEAM2_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "=== 개발 2팀 하네스 셋업 ==="
echo ""

# 0. TEAM2_HARNESS_PATH 등록
echo "[0/4] 팀 하네스 경로 등록..."

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
echo "[1/4] 팀 스킬 연결..."
mkdir -p "$CLAUDE_DIR/commands"

if [ -L "$CLAUDE_DIR/commands/ad" ]; then
    echo "  이미 심볼릭 링크 존재 — 갱신합니다."
    rm "$CLAUDE_DIR/commands/ad"
elif [ -d "$CLAUDE_DIR/commands/ad" ]; then
    echo "  기존 ad/ 디렉토리를 백업합니다 → ad.bak/"
    mv "$CLAUDE_DIR/commands/ad" "$CLAUDE_DIR/commands/ad.bak"
fi

ln -s "$TEAM2_DIR/.claude/commands/ad" "$CLAUDE_DIR/commands/ad"
echo "  ✓ ~/.claude/commands/ad → team2/.claude/commands/ad"

# 2. YouTrack 토큰 확인
echo ""
echo "[2/4] YouTrack 토큰 확인..."

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

# 3. gh CLI 확인
echo ""
echo "[3/4] gh CLI 확인..."

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

# 4. YouTrack MCP 확인
echo ""
echo "[4/4] YouTrack MCP 확인..."

if [ -f "$CLAUDE_DIR/mcp.json" ]; then
    if grep -q "youtrack" "$CLAUDE_DIR/mcp.json"; then
        echo "  ✓ YouTrack MCP 설정됨"
    else
        echo "  ⚠ YouTrack MCP가 ~/.claude/mcp.json에 없습니다."
        echo "  아래 내용을 추가하세요 (mcpServers 안에):"
        echo '    "youtrack": {'
        echo '      "type": "http",'
        echo '      "url": "https://aladincommunication.youtrack.cloud/mcp",'
        echo '      "headers": {'
        echo '        "Authorization": "Bearer {본인 YouTrack 토큰}"'
        echo '      }'
        echo '    }'
    fi
else
    echo "  ⚠ ~/.claude/mcp.json이 없습니다. 생성합니다..."
    echo '  토큰을 입력해야 합니다.'
    echo '  ~/.claude/mcp.json을 아래 내용으로 생성하세요:'
    echo '  {'
    echo '    "mcpServers": {'
    echo '      "youtrack": {'
    echo '        "type": "http",'
    echo '        "url": "https://aladincommunication.youtrack.cloud/mcp",'
    echo '        "headers": {'
    echo '          "Authorization": "Bearer {본인 YouTrack 토큰}"'
    echo '        }'
    echo '      }'
    echo '    }'
    echo '  }'
fi

echo ""
echo "=== 셋업 완료 ==="
echo ""
echo "사용법:"
echo "  아무 서비스 레포에서 claude 실행 → 팀 스킬 자동 사용 가능"
echo "  /ad:ticket          — 티켓 생성"
echo "  /ad:code-review     — PR 코드 리뷰"
echo "  /ad:team2-kb-read   — KB 문서 조회"
echo "  /ad:team2-kb-list   — KB 문서 목록"
echo "  /ad:team2-kb-sync   — KB → 하네스 동기화"
