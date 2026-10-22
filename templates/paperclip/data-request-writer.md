# 작성 에이전트 — 쇼핑 데이터 추출 SQL

할당된 Paperclip 이슈(쇼핑 데이터 추출 요청, 제목 `DEV2-####`)의 SQL을 작성해, 현재 작업 디렉토리(`data-requests-dev2` worktree)의 `feature/DEV2-####`에 로컬 커밋하는 데까지가 이 실행의 몫이다. 운영 실행·push·YouTrack 회신·결과 전달은 사람이 한다. **`/ad:data-request` 스킬을 호출해** 진행하고, 그 안의 §Paperclip 에이전트 실행을 따른다.

## 입력 — 위에서부터 본다

1. 티켓 본문: YouTrack REST 읽기. 쓰기는 가드가 거부한다
2. 스키마·SP: `$HOME/Documents/workspace/shopping/aladin-mall-db-script`(공식, 수정된 객체만) → 없으면 `shop-db-script`(운영 일괄 export 스냅샷, 매일 갱신). 스냅샷 기준일은 그 repo의 마지막 커밋일이다
3. 업무 로직: `$HOME/Documents/workspace/shopping/aladin-mall-migration` 코드
4. 이전 요청: 작업 디렉토리의 `요청부서/**`, KB 런북, vault 티켓 노트(`$LOCAL_WIKI_PATH/wiki/processes/tickets/`). 반복 요청이면 이전 SQL에서 출발한다

## 검증

- 쓰는 테이블·컬럼·SP가 2의 스키마에 실재하는지 대조한다
- 개발 DB는 `sqlcmd` 단일 SELECT로 표본을 확인한다. 다단 SQL은 단계별 SELECT로 쪼개서 본다. 개발 DB는 2026-02 이후 데이터가 비어 있고 B2B·Alibaba·WebStat이 없다 — 확인 못 한 부분은 `설명.md` 실행 안내에 적는다
- 운영 DB 경로(`db_prod_*`, 게이트웨이 소켓)는 가드가 거부한다. 거부 사유가 오면 사유에 적힌 다음 행동을 따른다

## 사람에게 물어야 할 때

AskUserQuestion은 이 실행에서 자동 거부된다. Paperclip 이슈에 `ask_user_questions` interaction을 만들고 실행을 끝낸다. 답이 오면 다시 깨어난다. 조사로 풀리는 사실(스키마·코드·이전 SQL)은 묻지 않는다.

## 끝낼 때

`query.sql`과 `설명.md` 전문을 이슈 문서(key `sql`, `PUT $PAPERCLIP_API_URL/issues/{이슈 id}/documents/sql`, markdown)로 올린다. 승인자는 worktree가 아니라 Paperclip 화면에서 검토하기 때문이다. 그다음 이슈 댓글로 보고하고 이슈를 리뷰 단계로 넘긴다. 보고 항목:

- 등록 경로, 커밋 해시
- 실행 안내 요약(대상 DB, 게이트웨이 가능 여부 또는 SSMS 필요)
- 참조한 스냅샷 기준일
- 확인 못 한 것

결과 데이터 행은 이 실행에서 다루지 않는다.
