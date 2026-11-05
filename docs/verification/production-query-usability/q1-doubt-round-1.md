# Q1 반증 검토 1차

- 검토자: fresh-context 내부 reviewer, 고정 gpt-5.6-sol / xhigh.
- 계약: 승인된 불변 요청 1회·새 중단 보존, 재접속/CSV에서 SQL 재전송 없이 정확한 승인 결과만 전달.
- 이 기록은 설계 검토이며 새 구현이 실행됐다는 증거가 아니다.

## 검토자가 제시한 반례

1. **P1 — export spec 승인 연결:** client의 다른 경로·컬럼 입력을 output_mode만으로 통과시키면 승인하지 않은 반출이 가능하다. 사양 전체의 digest 연결 또는 서버 봉투 파생이 필요하다.
2. **P2 — CSV와 metadata 공개:** CSV만 공개된 뒤 crash하면 NULL·타입·컬럼 metadata 없는 파일이 남을 수 있다. directory 단위 공개와 exporting intent/reconciliation이 필요하다.
3. **P2 — ack tombstone:** 메모리 정리 직후 응답 유실·재시작이면 already_delivered와 lost_on_restart를 구별할 근거가 없다. durable 전달 완료 기록이 필요하다.
4. **확인 못 함 — admitting 복구:** 현행 recovery phase와 파일 journal은 admitting을 다루지 않아 영구 슬롯 점유가 될 수 있다.

승인·슬롯 원자성 계약은 epoch·정확한 marker 집합·CAS·consumed+slot 단일 commit과 dispatch gate를 공격했지만 구체 우회 반례를 찾지 못했다고 보고했다.

## 메인 판정과 산출물 수정

- 1 수용: export spec을 불변 봉투에 포함하고 저장된 사양으로만 경로·컬럼을 파생한다. client는 식별자/digest만 참조한다.
- 2 수용: durable exporting intent와 CSV+manifest가 완성된 directory의 no-replace 공개, 불명확 상태 복구를 계약에 넣었다.
- 3 수용: ack tombstone을 제어 DB에 commit한 뒤 메모리를 정리한다. terminal metadata 30일, 미종결 상태는 TTL 정리 제외로 정했다.
- 4 수용: A의 동일 commit에 admitting 복구 정보를 기록하고 phase·소유권 fencing·새로 승인한 observer로 복구하는 경로를 명시했다. 현행 recovery 코드를 이미 지원하는 것으로 간주하지 않는다.

출력의 근거는 `/Users/jm/Documents/workspace/team2/docs/production-query-request-flow.md`의 갱신된 계약이며, 새 컨텍스트 2차 검토로 확인한다. 사용자 결정인 메모리 보관·이어받기·필요 시 CSV·v2 메모리 기본 32MiB도 같은 산출물에 반영했다.
