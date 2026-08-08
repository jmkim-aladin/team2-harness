---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

> 팀 오버라이드: 리뷰는 `/ad:code-review`(사용자 호출), 커밋 전 사용자 확인·`[이슈ID]` 형식 — policies/overrides/mattpocock.md

Implement the work described by the user in the spec or tickets.

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /code-review to review the work.

Commit your work to the current branch.
