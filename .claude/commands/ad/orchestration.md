---
description: Herdr pane peer-agent 협업 — 단발 위임, 다중 턴 핑퐁, 병렬 fan-out. HERDR_ENV=1 필요
---

# `/ad:orchestration`

Peer-agent coordination over Herdr panes. Symmetric: Claude may drive Codex or Codex may
drive Claude, same commands either way.

Default to a **conversation**, not a one-shot. A started peer keeps its session, so
follow-up prompts to the same name are contextual and cheap. Keep the pane alive until
the exchange is actually finished.

## 0. Caller or worker? Decide before touching anything

This file reaches both sides — Claude through `/ad:orchestration`, Codex through the
`ad-orchestration` skill, which reads this same file. That includes the peer that just
received an opening prompt. Everything from section 1 on assumes you are the **caller**.
If you are the worker, stop after this section — otherwise you rename yourself out from
under the caller's target and start orchestrating recursively.

Deciding your role is not itself a caller action: running the `HERDR_ENV` test and the
two read-only lookups below is allowed and expected before you know which side you are
on. Section 1 is where caller-only work starts.

Start with the free check: does the prompt that woke you carry a `HERDR_ROLE=worker`
envelope? Only when it does, resolve your live name. `pane current` gives your pane id,
but `.result.pane.agent` is the harness kind — not your role and not your name — so join
to `agent list`:

```bash
test "${HERDR_ENV:-}" = 1 || exit 1   # section 1's preflight applies here too, first
pane=$(herdr pane current --current | jq -r '.result.pane.pane_id')
herdr agent list | jq --arg p "$pane" \
  '.result.agents[] | {name, agent, agent_status, self: (.pane_id == $p)}'
```

Keep every agent in that output, not just your own row — branch 1 below has to confirm
that `HERDR_CALLER` is a *different live* agent, which you cannot do from your own row
alone. If the calls fail with `Operation not permitted`, you are a sandboxed Codex agent
— read section 1 before retrying.

Three branches, and there is no fourth:

1. Valid envelope whose `HERDR_TARGET` is your resolved name and whose `HERDR_CALLER` is
   a different live agent → **worker**.
2. No envelope, and the current user message explicitly asks you to open or drive a peer
   → **caller**. Continue to section 1.
3. Anything else — no envelope, mismatched target, name you can't resolve → do the work
   in front of you the way a worker would, and mutate no Herdr state. Absence of an
   envelope is never evidence that you are the caller; an older caller may simply not
   emit one, and a name alone proves nothing since callers name themselves too.

On branch 1 or branch 3: do the assigned task inside its stated read/write scope, then
answer normally in your own conversation and stay alive — the caller collects it with
`agent wait` / `agent read`. Do not rename or clear any agent name, do not
split/start/close/move/focus/take over panes, do not create another peer, do not touch
Herdr config or integrations, and do not prompt or wait on yourself.

Branch 1 only: ping `HERDR_CALLER` when blocked, when you need a decision, or when you
hold evidence that invalidates the task. On branch 3 there is no verified caller to ping
— raise it in your own answer instead.

## 1. Preflight (mandatory)

Second gate: sections 1–12 are caller-only. Nothing stops a worker from *reading* them —
one file loads whole — so re-check before acting. If section 0 landed you on branch 1 or
branch 3, you are done here; go do the assigned task. Only branch 2 continues.

```bash
test "${HERDR_ENV:-}" = 1 && herdr --skill   # chained: two statements, and $? hides the failed test
```

Test fails → you are not inside a Herdr-managed pane. Say so and stop; do not fall back
to Orca. `herdr --skill` prints the version-matched command surface and is
**authoritative for syntax** — this file holds only recipes and local conventions. If a
command below errors, re-read `herdr --skill` and its group (`herdr agent`,
`herdr pane`) rather than guessing flags.

**Codex callers:** probe before planning anything. A Codex agent without a bypass flag
can get `Error: Os { code: 1, kind: PermissionDenied, message: "Operation not permitted" }`
from `herdr` even though `herdr --skill` succeeded. Observed properties, not a theory:

- It is **not** uniform across the CLI. In one shell, `agent get` / `agent read` /
  `agent list` succeeded while `pane layout` failed with that error.
- It is **not** `$HERDR_PANE_ID` being unset — the variable resolves correctly, and the
  same id passed as a literal worked.
- Once the run is approved, the same commands succeed.

So do not assume the socket is either fully open or fully closed. Run one cheap probe
(`herdr pane layout --current`) before committing to a plan, and expect to escalate. Note
that starting the *peer* with a bypass flag does not grant *your own* access. Only the
caller needs it: the coordinator polls the pane, so the worker never calls back and a
worker with no socket access still works.

## 2. Resolve the peer, and name yourself

Peer kind defaults to the other of `claude` / `codex`. If the user named a kind, use
that. Both are installed.

Convention: caller is `<kind>0`, peers are `<kind>1`, `<kind>2`. Check `herdr agent
list` before picking so you don't collide with a pane the user already has open.

Name yourself only if your pane has no name yet, and remember that you were the one
who set it:

```bash
herdr agent rename "$HERDR_PANE_ID" claude0    # or codex0 when you are Codex
```

Never overwrite an existing name — it may be the address someone else is already
holding. Without any name the peer cannot reach you and the flow is one-way.

## 3. Open the peer

Layout and split per `herdr --skill`. Standing user policy on this machine: start every
peer with its harness bypass flag, passed after `--`.

```bash
herdr agent start codex1  --kind codex  --pane <pane_id> --timeout 60000 \
  -- --dangerously-bypass-approvals-and-sandbox
herdr agent start claude1 --kind claude --pane <pane_id> --timeout 60000 \
  -- --dangerously-skip-permissions
```

Bypass removes the harness permission boundary; it does not widen the task
authorization. State the exact read/write scope in the opening prompt — that is now
the only boundary the peer has. A bypassed peer reaches the Herdr socket, so it can
send keys into your pane and answer your approval UI on your behalf, forge lifecycle
state on other panes (`pane report-agent`, `release-agent`) so someone's `wait`
returns at the wrong moment, alter integration hooks, and edit this shared skill.
Tell it in the prompt that it must not.

Do not pass `--profile fast` / `service_tier` overrides to a Codex peer.

`pane split` returns before the new shell reaches its prompt, so an immediate
`agent start` can fail with `agent_pane_busy` — "agent target pane is not an available
shell". That is a race, not a real error: the pane is fine, just not ready. Retry the
same command.

### Model routing

Pick the peer's role from the work, then start it with that role's model and effort.
Never leave them implicit.

Model line-ups change. The line-up in effect is whatever `herdr --help` or the team
announcement says; the table below is a 2026-08 snapshot, so verify the model id before
relying on it.

| role | use for | Codex model | effort |
|---|---|---|---|
| `worker` | implementation, exploration, investigation, documentation | `gpt-5.6-luna` | `max` |
| `orchestrator` | decomposing work, assigning agents, synthesizing results | `gpt-5.6-sol` | `xhigh` |
| `reviewer` | correctness, security, regression review | `gpt-5.6-sol` | `xhigh` |
| `verifier` | tests, acceptance criteria, done-conditions | `gpt-5.6-sol` | `xhigh` |

Codex peer — routing flags go after `--`, alongside the bypass flag:

```bash
herdr agent start codex1 --kind codex --pane <pane_id> --timeout 60000 \
  -- --dangerously-bypass-approvals-and-sandbox \
     -m gpt-5.6-sol -c 'model_reasoning_effort="xhigh"'
```

Claude peer — **never** forward `-m` or `model_reasoning_effort`; those are Codex-only
and Claude picks its model natively. Pass Claude's own options and nothing else:

```bash
herdr agent start claude1 --kind claude --pane <pane_id> --timeout 60000 \
  -- --dangerously-skip-permissions
```

Every freshly started peer prints this once, as the first line of its first
user-visible response:

```text
[model] role=<role> model=<model> effort=<effort>
```

The logged values must equal what you actually passed on the command line. Do not repeat
it on follow-up turns. A new process, a new agent, a handoff between AIs, and a run
resumed from outside are each a fresh start point. Never guess a value you cannot
confirm — print `unknown`.

Outside Herdr, when shelling out to Codex directly, `-m` must come **before** the
subcommand for `review`. Verified: `codex review -m <model>` fails with
`error: unexpected argument '-m' found`.

```bash
codex -m "$MODEL" -c "model_reasoning_effort=\"$EFFORT\"" review "$PROMPT"
codex exec -m "$MODEL" -c "model_reasoning_effort=\"$EFFORT\"" "$PROMPT"
```

## 4. One exchange (the primitive)

```bash
herdr agent prompt codex1 "<text>" --wait --timeout 600000
herdr agent read   codex1 --source recent-unwrapped --lines 200
```

Repeat this pair for every turn. Sections 5 and 6 are policies over it.

**The first prompt after `agent start` is the one that breaks.** Bracketed paste may not
be live yet, so a multi-line prompt can submit only its first line — and the agent's
startup lifecycle transition satisfies `--wait` anyway, so you get a success return on a
truncated prompt. The envelope template below makes this maximally likely, since it puts
three short lines first. After the *first* prompt to a freshly started agent, always
`agent read` and confirm the tail of your text is actually on screen before trusting the
result. If only the first line landed, resend the whole prompt — the agent never saw the
rest, so there is nothing to duplicate.

### Opening prompt

The peer starts with no shared context. Lead with the worker envelope so section 0
fires on the other side:

```text
HERDR_ROLE=worker
HERDR_CALLER=claude0
HERDR_TARGET=codex1
HERDR_TASK_ROLE=reviewer
HERDR_MODEL=gpt-5.6-sol
HERDR_EFFORT=xhigh
```

The first three drive section 0's branch. The last three are the handoff record — the
same `role` / `model` / `effort` you passed at `agent start`, restated so the peer can
emit its `[model]` line and so the exchange is auditable from the transcript alone. Add
`HERDR_SESSION=<id>` when resuming a known session. When the peer is Claude, still send
`HERDR_TASK_ROLE`, but leave `HERDR_MODEL` / `HERDR_EFFORT` off or set them to `unknown`
— you did not choose them, so do not assert them.

Then give: the repo path, the exact files or diff range, what to produce, the
read/write scope stated explicitly, and that a conversation is expected. Ask for
findings, not narration. Tell it to run
`herdr agent prompt claude0 "<question>"` when blocked or when it needs a decision,
instead of guessing.

The peer is started bypassed, so copy section 3's prohibitions into the prompt itself.
The sandbox is no longer saying them for you.

## 5. Ping-pong (default for review, design, disagreement)

Loop section 4 against the same agent name. Do not restart the agent, do not close
the pane between turns — restarting throws away its context and makes the exchange
worse than a single shot.

Each of your turns must add something: an answer to its question, a counter-argument
with evidence, a narrowed scope, or a verdict. Never relay a bare "ok, continue".
Read its actual output before composing the next turn — quote the specific claim you
are responding to.

Standard shapes:

- **Cross-review** — you propose, peer critiques, you revise or rebut, peer confirms
  or holds. Typically 2–4 exchanges.
- **Adversarial check** — ask the peer to refute a specific claim, defend it with
  evidence, then ask whether the refutation still stands.
- **Design debate** — each side states an approach and its failure mode, then you
  converge or record the trade-off.

Stop when one holds:

1. **Converged** — the peer agrees, or its remaining objections are ones you accept.
2. **Stable disagreement** — a round produces no new argument on either side.
   Report both positions to the user; do not keep looping to manufacture agreement.
3. **Round cap** — default 5 exchanges; adjust if the topic warrants. Report where it
   stands.
4. **Off the rails** — the peer is hallucinating files or looping. Stop, say so, and
   fall back to doing it yourself.

Never accept the peer's output just because it came from another model — verify claims
about the code against the code. A confident peer that is wrong is the main risk here,
and the final answer is yours either way.

## 6. Peer-initiated pings (the reverse direction)

Because you registered a name in section 2, the peer can prompt you back:

```bash
herdr agent prompt claude0 "<question>"     # run BY the peer, targeting you
```

It arrives as an ordinary user turn. When you are idle it starts a new turn; while you
are working it may be queued or treated as steering, so mid-turn delivery is not
guaranteed. **Nothing in the payload authenticates the sender** — a claim of "I am
codex1" inside the text is unverified. Act on the content, not on the claimed origin,
and keep the user informed of what was exchanged.

Rules:

- Never `agent prompt` your own name — self-deadlock. Never `agent wait` on yourself
  either: your own lifecycle is `working` while the command runs, so it cannot observe
  your completion and will sit until timeout or return early on an unrelated `blocked`.
- Tell the peer *when* to ping back (blocked, needs a decision, found something that
  invalidates the task). Unsolicited pings interrupt your turn.
- If a ping arrives mid-work, finish the atomic step you are on, then respond. Do not
  abandon a half-applied edit.

## 7. When a wait comes back `blocked`

```bash
herdr agent get  codex1
herdr agent read codex1 --source recent-unwrapped --lines 120
```

- Inspect the rendered UI before answering: explicit accept/reject keys for an
  approval, displayed navigation plus `enter` for a choice, and
  `herdr agent prompt codex1 "<answer>"` for a free-text question. `blocked` is any
  approval *or question* UI, not always a keypress.
- Never send `enter` or `y` without verifying what is selected. `unknown` state is not
  proof of completion.
- On `agent_prompt_stalled` (semantics: `herdr --skill`), inspect with `agent get` /
  `agent read` and resend only with evidence that submission failed, or you duplicate a
  task already running.

## 8. Truncated output fallback

`herdr --skill` covers the alternate-screen fallback: when a larger `--lines` reveals
nothing new, have the peer write its answer to a temp file and reply with the path.

Raise `--lines` first and actually check — the pane holds more than you expect. Measured
on a deliberately long answer: `--lines 60` returned 59 rows, `--lines 400` returned 360.
The fallback is for when that stops helping, not for every long answer.

The part it does not cover: **that is a write.** If you told the peer read-only, you
cannot quietly grant yourself the exception — ask the user to widen the scope, or ask
the peer to resend in chunks with no file. Only when writes were already authorized may
you name the `$TMPDIR` path yourself.

## 9. Parallel fan-out (when turns are independent)

Split and start every pane first. Then, **before dispatching anything**, confirm each
peer is actually settled:

```bash
herdr agent get codex1 | jq -c '.result.agent | {agent_status, interactive_ready}'
```

Use `agent get`, not `agent wait` — a plain state read with no wait semantics. This step
is not optional in fan-out: the peer you started last is still coming up while you write
the first dispatch, and its startup lifecycle transition will satisfy `prompt --wait` on
its own, handing you a return on an empty turn. That is the exact failure the rest of
this section warns about, reproduced by this section's own sequencing.

Then run one `prompt --wait` per peer **concurrently** — backgrounded, not sequentially —
and read each as it returns. Every one of those is a first prompt to a freshly started
agent, so section 4's verification applies to all of them, not just the one you happen to
look at.

Do not dispatch without `--wait` and collect with a standalone `agent wait`: standalone
wait accepts an already-settled `idle` / `done` / `blocked`, so it returns on the stale
pre-prompt state and you read the previous turn. Measured: `prompt` without `--wait`
returned `idle`, and a standalone `wait` fired immediately after returned in 0s, still
`idle`, before the agent had transitioned to `working`.

Use this only when the tasks genuinely don't need to talk to each other. If they do,
that's section 5.

## 10. Ordinary command in a sibling pane

`pane split` → `pane run` → `pane wait-output` → `pane read`, per `herdr --skill`.
Use `pane` for processes, `agent` for recognized coding agents.

`wait-output` searches the existing snapshot immediately, and **the pane echoes the
command line you typed**. Both bite:

- `--match "Tests:"` matches stale output from an earlier run, and a command that exits
  without ever printing it waits to timeout.
- A sentinel that appears literally in the command — `echo "DONE_x rc=$?"` matched by
  `--match "DONE_x rc="` — matches the echoed command line itself and returns in 0s,
  every run, even with a fresh random token. Measured: 0s against a `sleep 15`.

So the match string must never appear literally in what you type. Assemble it at runtime
with `printf` and match the assembled form:

```bash
S=$(openssl rand -hex 4)
herdr pane run <pane_id> "npm test; rc=\$?; printf 'DONE%s rc=%s\n' \"$S\" \"\$rc\""
herdr pane wait-output <pane_id> --match "DONE$S rc=" --timeout 600000
```

The typed line holds `printf 'DONE%s rc=%s\n' "<hex>"`; the string `DONE<hex> rc=` only
ever exists in real output. Verified: waits the full command duration, and carries the
exit status (`rc=1` on failure).

## 11. Cleanup and boundaries

- Close only panes you created, and only once the exchange is done:
  `herdr pane close <pane_id>`. Leaving a peer alive is correct while the topic is
  still open.
- Clear your name only if section 2 is what set it:
  `herdr agent rename "$HERDR_PANE_ID" --clear`. Never clear a name you did not create.

## 12. Install notes

Install state (hooks, symlinks, where this file lives) is owned by
`harness.manifest.json` and `tools/setup_harness.py` — check there, and run
`herdr integration status` when `--wait` degrades to a plain timeout.
