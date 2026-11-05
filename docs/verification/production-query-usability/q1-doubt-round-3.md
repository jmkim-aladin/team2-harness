# Q1 반증 검토 3차와 메인 종료 판정

새 컨텍스트 내부 reviewer(gpt-5.6-sol / xhigh)가 현행 계약 두 개를 검토했다. 외부 벤더 전송이나 운영 접근은 없었다. 반증 검토의 상한 3라운드로 종료한다.

## 3차 반례

1. **P1 — ready 경로와 외부 halted 혼용:** A/B에서 항상 halted=1로 바꾸면 execute-only 승인이 어떤 halt를 해제하는지 명확하지 않다. 외부 중단과 내부 admission gate를 분리하고 ready/resume 전이표가 필요하다.
2. **P1, Q3b 출시 gate — 스트리밍 전 최종 hash 요구:** 큰 CSV를 bounded streaming으로 쓰면서 intent가 최종 result digest를 먼저 요구하면 계약을 실행할 수 없다. stream identity와 EOF 이후 content digest를 분리하고, 재시작 비교에 필요한 canonical export spec을 manifest에도 보관해야 한다.

그 외 접수 응답 유실·중복 승인·gateway 손실·새 중단·fetch/ack 경로에서 추가 자동 SQL 재전송 반례를 찾지 못했다고 보고했다. 신규 코드와 설치별 frame/RSS 구현 검증은 미수행으로 구별했다.

## 산출물 수정과 메인 판정

- 1 수용·설계 반례 해소: 내부 gate는 기존 영속 phase=admitting으로 표현한다. ready A/B/C는 외부 halted/epoch를 쓰지 않는다. 소유 active 슬롯이 경쟁 admission을 막고 phase가 dispatch를 막는다. resume 경로에서만 정확한 승인 snapshot의 halt를 C CAS로 해제한다. 각 전이와 새 stop 거부를 canonical 문서의 표로 고정했다.
- 기존 Store의 해당 메커니즘을 로컬 임시 SQLite에서 실제 확인했다. 다른 reserve=busy, admitting dispatch 거부, ready starting fixture의 1회 dispatch, 재dispatch 거부, 새 stop 뒤 dispatch 거부를 관측했다. [q1-core-gate-probe.py](./q1-core-gate-probe.py)는 v2 admission 구현이 아니라 기존 gate의 재사용 가능성을 확인하는 격리 probe다.
- 2 수용·설계 반례 해소: 쓰기 전 durable intent에는 stream ID와 request/spec lineage만 고정한다. EOF·codec·성공/종료·제어 commit 확인 뒤에 content/CSV digest·길이·건수를 completion으로 기록한다. completion 없는 staging은 publish하지 않는다. manifest에는 canonical spec 전체를 넣어 원장의 spec digest와 비교한다.

메인은 위 반례의 순서를 수정된 상태표·intent/completion 계약으로 다시 추적해 해당 모순이 남지 않았다고 판정했다. **수정본에 대한 4차 fresh-context 반증은 수행하지 않았다.** 신규 v2 gate·streaming·원자적 directory 공개·장애 복구가 구현됐다는 주장은 하지 않는다. 해당 assert는 Q2/Q3/Q3b의 P1 구현·출시 검사로 유지한다.

## 결정 패킷

- 승인·중단: 3라운드 / 실제 action digest·admitting 복구·외부 halt/내부 phase 분리로 제기된 반례를 계약에 반영 / 남은 구현 의무: marker·SQLite·process crash와 다중 프로세스 검증.
- 결과·CSV: 3라운드 / immutable fetch·durable ack·server-owned spec·directory 공개·사전 stream ID/사후 content completion으로 제기된 반례를 계약에 반영 / 남은 구현 의무: 실제 framing·타입 보존·메모리·파일 공개/재시작 검증.

미결 정책 선택은 없다. 결과 cache TTL/상한·terminal metadata 보존과 새 CSV 형식은 canonical 문서에 명시했다. 신규 설계 동작을 동적 검증한 것처럼 보고하지 않는 조건으로 Q1 문서·설계 검증 범위를 종료한다.
