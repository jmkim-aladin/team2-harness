# cmux/herdr 작업 라벨 규칙

작업 컨텍스트(티켓)를 터미널 멀티플렉서 라벨에 반영하는 공용 절차. `ad:work-prep` §9 등에서 호출한다.
cmux/herdr 외부(일반 터미널/tmux/iTerm/VSCode 내장 등)에서는 **건드리지 않는다**.

## 감지

```bash
CMUX_INSIDE=0
if [ -n "${CMUX_WORKSPACE_ID:-}" ] && [ -n "${CMUX_SURFACE_ID:-}" ] && command -v cmux >/dev/null 2>&1; then
  CMUX_INSIDE=1
fi

HERDR_INSIDE=0
if [ -n "${HERDR_ENV:-}" ] && [ -n "${HERDR_PANE_ID:-}" ] && command -v herdr >/dev/null 2>&1; then
  HERDR_INSIDE=1
fi
```

## 리네이밍

```bash
# 티켓 모드
TAB_LABEL="DEV2-{NNNN}"
PANE_LABEL="DEV2-{NNNN} — {제목}"

# 자유글 모드라면 위 대신:
# TAB_LABEL="NO-TICKET"
# PANE_LABEL="NO-TICKET — {제목}"

# cmux 안이면 surface tab 이름 변경
if [ "$CMUX_INSIDE" -eq 1 ]; then
  cmux rename-tab --surface "$CMUX_SURFACE_ID" "$TAB_LABEL"
fi

# herdr 안이면 현재 tab + agent + pane 이름 변경
if [ "$HERDR_INSIDE" -eq 1 ]; then
  HERDR_TAB_ID="$(herdr pane get "$HERDR_PANE_ID" | jq -r '.result.pane.tab_id')"
  herdr tab rename "$HERDR_TAB_ID" "$TAB_LABEL"
  herdr agent rename "$HERDR_PANE_ID" "$TAB_LABEL"
  herdr pane rename "$HERDR_PANE_ID" "$PANE_LABEL"
fi
```

## 규칙

- 티켓 모드는 tab/cmux surface에 `DEV2-{NNNN}`만 표시한다. 제목은 herdr pane label에만 둔다.
- 자유글 모드는 tab/cmux surface에 `NO-TICKET`만 표시하고, herdr pane label은 `NO-TICKET — {제목}`으로 둔다.
- 제목은 한 줄로, 약 60자 이내로 자른다 (pane 폭 고려).
- 명령 실패(소켓 인증 실패, 서피스·pane ID 만료 등)는 경고만 출력하고 다른 단계를 막지 않는다.
- cmux 워크스페이스 자체 이름(`workspace-action --action rename --title ...`)은 건드리지 않는다 — 사용자가 별도 작업 컨텍스트로 쓰고 있을 수 있다. 탭(=surface) 단위만 변경한다.
- herdr 워크스페이스 이름은 건드리지 않는다. 현재 tab/agent label은 티켓번호만, 현재 pane label은 제목 포함으로 변경한다.
- 사용자 확인 없이 기본 진행. 변경 전후 이름을 출력에 명시한다.
