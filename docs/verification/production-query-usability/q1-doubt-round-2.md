# Q1 반증 검토 2차

새 컨텍스트 내부 reviewer(gpt-5.6-sol / xhigh)가 동일한 계약 두 개로 갱신된 산출물을 검토했다. 1차 기록·작성자 대화는 전달하지 않았다.

## 검토자가 제시한 반례

1. **P1 — 실제 선택 action과 digest 분리:** 허용 action 집합만 봉투에 있고 client가 별도 explicit_actions를 전달하면 execute만 승인한 것을 resume+execute로 확대할 수 있다.
2. **P1 — 원 결과 export가 새 조회로 바뀜:** 원 결과가 plain text일 때 export 경로에서 새 구조화 SQL을 승인받아 실행하면 다른 시점의 다른 결과를 원 결과 export처럼 전달할 수 있다.

A/B/C crash, 새 epoch·marker, 같은 ID·다른 digest와 gateway 손실 뒤 SQL 무재전송은 계약의 방어 지점을 확인했다고 보고했다. 설치별 HEX frame·RSS·타입 보존은 명시된 구현/출시 gate로 구별했다.

## 메인 판정과 수정

- 1 수용: 서버가 각 검토의 실제 action 집합을 확정·표시한다. approval_digest는 envelope digest·request ID·정렬된 selected_actions를 묶고 A가 정확히 대조·보존한다. 부분 승인이나 action 추가는 재개·실행 없이 거부한다.
- 2 수용: export API는 구조화 결과·원 승인 spec이 없으면 not_exportable로 끝난다. 사용자가 별도 새 조회를 요청할 때만 새 request/result lineage·전체 SQL·승인을 사용하며 “원 결과 내보내기”라고 표시하지 않는다.
- ack 직후 메모리 정리 전의 동시 읽기도 durable delivered를 확인해 bytes 반환을 거부하도록 명시했다.

마지막 3차 fresh-context 검토에서 현행 산출물을 반증한다. 이 기록의 수용은 설계 수정 판정이며 아직 코드 반영·실행 검증이 아니다.
