---
name: "source-command-ad-code-review"
description: "사용자가 source-command-ad-code-review라는 기존 호출 이름을 명시했을 때만 팀 source command를 실행한다."
---

# source-command-ad-code-review

기존 호출 이름을 유지하는 얇은 alias다. 리뷰 절차는 팀 하네스의 source command 하나를 사용한다.

1. `TEAM2_HARNESS_PATH`를 사용하며 기본값은 `/Users/jm/Documents/workspace/team2`다.
2. 다른 도구보다 먼저 `$TEAM2_HARNESS_PATH/.claude/commands/ad/code-review.md`를 읽고 그 절차를 따른다.
3. 해당 문서의 범위·검증·미리보기·게시 권한을 그대로 적용한다. 이 alias에 리뷰 본문이나 별도 승인 기준을 복제하지 않는다.
