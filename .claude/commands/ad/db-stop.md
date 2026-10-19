---
description: 현재 Mac 계정의 운영 DB 조회를 취소하고 종료 확인 상태를 점검
---

# 운영 DB 조회 취소

`/ad:db-stop`, `$ad-db-stop`, 또는 운영 DB 조회를 멈추라는 요청으로 호출한다. 이 명령은 현재 Mac 사용자 계정의 실행 중인 운영 조회를 취소하고 기존 준비·승인을 무효화한다. 오류 없는 사용자 취소로 서버 종료가 확인되고 `active=null`, `phase=idle`이 되면 일시 중단을 자동 해제해 다음 요청을 받을 수 있게 한다. 오류·timeout은 종료가 확인돼도 active 슬롯만 정리하고 차단을 유지하므로 명시적 `resume`이 필요하다. 새 SQL은 항상 새 검토·승인이 필요하다. 지속적인 전체 차단은 별도 `emergency-stop` 명령으로 요청한다.

현재 작업 디렉터리와 관계없이 같은 Mac 사용자 계정의 운영 실행기를 대상으로 한다. lego-prod·cool-prod를 포함해 이 실행기를 사용하는 모든 에이전트 세션이 대상이다. 개발 DB, 별도 DataGrip 연결, 다른 Mac·사용자 계정은 이 실행기의 통제 대상이 아니다.

## 실행

사용자의 중단 요청이 실행 승인이다. 추가 확인·DB 연결·사전 상태 조회 없이 아래 명령부터 실행한다 — 실행기가 응답하지 않아도 독립 중단 파일부터 기록해야 취소가 지연되지 않는다. 현재 실행과 대기 중인 기존 승인을 무효화하는 것은 이 취소의 일부다.

```bash
python3 /Users/jm/Documents/workspace/team2/tools/db_prod_client.py stop
```

그 다음 로컬 상태를 확인한다. 이 명령은 SQL을 실행하지 않는다.

```bash
python3 /Users/jm/Documents/workspace/team2/tools/db_prod_client.py status
```

## 결과와 경계

- `latch_persisted=true`는 중단 요청을 기록했다는 접수 증거이고, `latch_active`는 자동 정리 후 현재 중단 파일의 존재 여부다. `request_marker`는 이미 처리한 요청의 식별자다. `coordinator_updated=false` 또는 status 실패는 함께 알린다. 실행기 장애여도 이미 기록된 중단 파일은 유지한다.
- `halted`, `active`·`phase`를 구분해 보고한다. 오류 없는 사용자 취소에서 서버 종료가 확인되고 `active=null`, `phase=idle`이면 일반 `stop`의 일시 중단 latch가 자동 해제되어 다음 요청을 준비할 수 있다. 이때도 기존 승인은 복원하지 않으며 새 SQL 승인이 필요하다.
- `active`가 남거나 `phase`가 idle이 아니면 종료 확인 중 또는 미확인 상태다. 서버 세션 종료 확정에는 실행기의 실제 관찰 결과가 필요하다 — 요청 접수와 서버 종료는 별개 상태다. 종료 미확인·실행기 재시작 후 차단은 자동 해제하지 않는다. 오류·timeout은 서버 종료 증거와 `active=null`, `phase=idle`이 함께 확인되면 active 슬롯만 정리하고 차단은 유지하므로 명시적 `resume`이 필요하다.
- 서버 종료 확인은 이미 승인된 실행기의 정리 경로가 수행한다. 실패로 확정된 실행의 복구 조회는 SQL 전문과 한도를 제시해 별도 승인을 받는다 — 중단 요청은 추가 운영 SQL의 실행 승인이 아니다.
- 차단·원장·기존 실행의 신원을 보존하고, 취소는 이 실행기가 소유한 프로세스에 대한 중단 경로만 사용한다 — 다른 세션의 신규 실행과 잘못된 종료를 막기 위해서다. `emergency-stop`으로 지속 차단된 경우에는 사용자의 별도 `resume`이 필요하다.
- `python3 /Users/jm/Documents/workspace/team2/tools/db_prod_client.py emergency-stop`은 일반 `stop`과 달리 서버 종료가 확인돼도 차단을 유지한다. 장애 대응이나 운영자가 명시적으로 전체 접근을 잠글 때만 사용한다.
- 명령 파일이 없거나 실행에 실패하면 해당 오류와 중단 성공 여부 미확인을 알린다. 등록·설명만 요청한 경우에는 설치·안내로 작업 범위를 한정한다 — 실제 중단은 사용자의 중단 요청에 따른다.

정책: `/Users/jm/Documents/workspace/team2/docs/production-db-emergency-stop.md`. 상세 점검에 필요할 때 읽으며 긴급 중단 실행의 선행 조건으로 삼지 않는다.
