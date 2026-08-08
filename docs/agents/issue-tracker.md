# Issue tracker: YouTrack (DEV2)

mattpocock 계열 스킬(`wayfinder` 등)이 읽는 이슈 트래커 설정. 이 저장소의 이슈는 YouTrack DEV2 프로젝트에 산다.

- 접근: REST API만 (`$YOUTRACK_TOKEN`, `$YOUTRACK_BASE_URL`). MCP 미사용
- **이슈 생성·분할은 `/ad:ticket` 절차를 따른다** — 5W1H 본문, Feature ≤ 1주, Task ≤ 1일, SP 상한 3, Assignee 필수, 토큰 owner 검증. 5W1H·SP 규칙의 SoT는 [ticket-guide.md](../sprint/ticket-guide.md)·[story-point-guide.md](../sprint/story-point-guide.md)이고, [`/ad:ticket`](../../.claude/commands/ad/ticket.md)은 그 절차 구현이다
- 조회: `GET /api/issues/DEV2-XXXX?fields=idReadable,summary,description,customFields(name,value(name,login))`
- PR을 요청 표면으로 쓰지 않는다 (외부 PR 트리아지 없음)

## Wayfinding operations

`/wayfinder`가 쓰는 매핑. **맵**은 YouTrack 이슈 하나, 티켓은 그 하위 이슈다.

- **Map**: DEV2 이슈 + 태그 `wayfinder-map`. 본문이 Destination / Notes / Decisions-so-far / Not-yet-specified / Out-of-scope
- **Child ticket**: 맵의 subtask 링크로 연결된 DEV2 이슈. 본문 `## Question`. 유형은 태그 `wayfinder-research|prototype|grilling|task`
- **Blocking**: YouTrack 네이티브 `is blocked by` 링크
- **Claim**: Assignee 설정이 곧 claim — 열려 있고 Assignee 없는 티켓이 unclaimed
- **Frontier**: 열림 + unblocked + unclaimed 하위 이슈. 쿼리: `subtask of: {맵ID} #Unresolved has: -Assignee`
- **Resolve**: 답을 resolution 코멘트로 게시 → 상태 Fixed → 맵 본문 Decisions-so-far에 한 줄 + 링크 추가

이슈·태그·링크 생성은 사용자 확인 후 수행한다 (팀 INVARIANT).
