# Docker SQL Server DB 접근 검증

개발 DML 허용과 운영 최소 조회 권한을 합성 데이터로 검증한다. 실제 개발/운영 DB 접속이나 자격증명 조회는 수행하지 않는다. 정책: [개발 DB](../../../../policies/local-credentials-policy.md) · [운영 DB](../../../../policies/production-db-access-policy.md).

## 실행

repo 루트에서:

```bash
python3 tools/tests/integration/sqlserver/verify.py \
  --report docs/verification/sqlserver-db-access-local.json
```

Docker와 SQL Server 2022 AMD64 이미지가 필요하다. 기본 태그는 `2022-CU24-GDR1-ubuntu-22.04`이며 로컬에 없으면 내려받는다. `--image mcr.microsoft.com/mssql/server@sha256:...`로 digest를 고정할 수 있다. 실행 시 실제 image ID/digest와 서버 버전을 결과 JSON에 기록한다.

SQL Server Developer 컨테이너를 `ACCEPT_EULA=Y`로 실행한다. 메모리 상한은 2560MiB, CPU는 2개이며 Docker 호스트에는 다른 작업과 SQL Server를 함께 구동할 여유가 필요하다. ARM Mac에서는 AMD64 에뮬레이션으로 동작한다. Microsoft는 이 에뮬레이션 구성을 지원·검증하지 않으므로 기능 재현 결과를 운영 성능/지원성 검증으로 해석하지 않는다. [Microsoft 배포·지원 범위](https://learn.microsoft.com/en-us/sql/linux/containers/deploy), [공식 컨테이너 시작 가이드](https://learn.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker)

## 격리와 정리

- 실행마다 고유한 `team2-db-policy-test-*` 컨테이너를 만든다. 네트워크는 `none`, 공개 포트와 호스트/기존 볼륨 마운트는 없다.
- SQL은 해당 컨테이너 내부 `tcp:127.0.0.1,1433`으로만 실행한다. 실제 개발 호스트 문자열은 로컬 훅 판정 함수의 입력으로만 사용하며 DNS 조회/접속하지 않는다. 운영 allowlist에 localhost를 추가하지 않는다. 격리 네트워크에서 `localhost` 이름의 ODBC 접속이 실패하는 경우를 피하려고 주소와 포트를 명시한다.
- fixture 설치만 임시 `sa`를 사용하고, 권한 판정은 각 제한 계정의 별도 로그인으로 확인한다. 계정 비밀번호는 실행마다 메모리에서 생성해 환경변수로 전달한다. SQL 본문은 stdin으로 전달한다.
- 종료·실패·중단 시 자신이 만든 컨테이너와 연결된 익명 볼륨만 삭제한다. 기존 컨테이너/이미지에는 prune·stop을 실행하지 않는다. 내려받은 이미지는 재사용을 위해 남긴다.
- 테스트 비밀번호는 실행 중 Docker 관리자에게 보일 수 있다. 컨테이너 삭제로 수명을 끝내며 운영 자격증명을 넣지 않는다. 강제 프로세스 종료/SIGKILL·Docker 장애 때는 JSON 또는 `docker ps -a --filter label=team2.fixture=db-access`로 잔여 컨테이너를 확인해 해당 테스트 것만 정리한다.

## 판정

| 범위 | 검증 |
|---|---|
| 개발 | 직접 sqlcmd DML 차단과 전용 실행기의 INSERT/UPDATE/DELETE 커밋·반영 건수 확인 |
| 개발 권한 | 직접 DDL/프로시저/권한 확대/다른 DB 접근을 시도해 SQL Server 오류 번호 확인 |
| staging | SELECT 허용, INSERT/UPDATE/DELETE 거부 |
| 운영 모사 | 허용 뷰 조회, 원본 테이블·뷰의 민감 열·쓰기·EXEC·DDL 거부, SP 생성·변경·삭제 거부와 정의 보존 |
| 부하 제한 일부 | 실제 잠금 충돌에 `LOCK_TIMEOUT` 오류 1222, sqlcmd query timeout 후 서버 세션 종료 |
| 개발 행 수 | 150행 변경 전체 롤백, 작업 누적 60+50 거부·60+40 허용·추가 실행 차단 |
| 불명확 결과 | timeout 후 롤백·세션 잠금 해제 확인, 커밋 응답 유실 후 성공 오판·자동 재시도 차단 |
| 부작용 | 활성 트리거 테이블을 DML 전에 거부하고 원본 데이터 보존 |
| 동시 DDL | 메타데이터 검사 전 테이블 잠금 관측, 다른 세션의 트리거 생성 거부와 부작용 부재 |
| 운영 격리 | NOLOCK의 dirty read, 일반 READ COMMITTED의 잠금 대기, RCSI의 커밋된 값 조회, NOLOCK도 Sch-M에서 대기함을 재현 |
| 비상 중단 DB 수단 | 전용 로그인 신규 접속 차단, 기존 두 세션 별도 종료, 다른 로그인 세션 보존, 읽기 계정의 차단 해제 거부 |
| 중앙 제어 | 미승인 접속 거부·전역 슬롯 경쟁·별도 stop CLI·오류/timeout 취소·서버 종료 확인·재개 전 차단·과거 승인 무효 |

DDL/DML의 예상 거부는 명령 실패만으로 통과시키지 않고 SQL Server 오류 번호까지 대조한다. 권한 확대 시도는 실제 유효 권한과 후속 ALTER 거부를 확인한다. query timeout은 사전 성공 연결, 실행 중 WAITFOR의 session ID, 정확한 timeout 메시지와 경과 시간, 동일 세션 소멸을 확인한다. 이 이미지의 ODBC sqlcmd는 `Timeout expired`를 출력하면서 종료 코드 0을 반환할 수 있어 종료 코드만으로 판정하지 않는다.

결과의 `checks[].passed`는 해당 기대 결과와 일치한다는 뜻이다. 과거 보고서의 `known limit` 검사는 **당시 제한이 강제되지 않음의 재현 성공**이다. 현재 검증은 전용 개발 실행기의 초과 롤백을 확인한다. 로컬 원장·코드는 수정 가능하므로 임의 드라이버와 다른 작업 ID까지 통제하는 운영 보안 경계는 아니다. 보고서의 `production_ready`는 false이며 운영 개통 승인으로 사용하지 않는다.

이번 fixture는 중앙 제어 코어의 단일 슬롯·일회 승인·중단 상태 전이를 검증하지만 실제 운영 실행기·사용자 인증·승인 서명·감사 장애·행/바이트 스트리밍 반환 제한을 구현하거나 검증하지 않는다. 호스트의 실제 Claude/Codex 훅 등록도 검증하지 않는다. 중앙 코어·테스트 adapter·DB 권한의 범위를 분리해서 판단한다.

개발 실행기의 public 함수에 컨테이너 전용 transport와 임시 원장을 주입한다. 실제 CLI의 개발 서버 접속이나 호스트 sqlcmd 버전 호환성 검증은 별도다. 격리 수준 변경은 자신이 생성한 `IsolationFixture`에서만 수행하며 실제 운영 설정 변경을 뜻하지 않는다.

## 기록된 실행

[2026-10-14 결과 JSON](../../../../docs/verification/sqlserver-db-access-2026-10-14.json): SQL Server 2022 `16.0.4250.1`, 40개 기대 결과 일치, 컨테이너 정리 완료. 비키 조건 150행 변경 가능성과 timeout의 exit code 0도 재현해 기록했다. 운영 개통 상태는 false다.

[2026-10-14 보완 후 결과 JSON](../../../../docs/verification/sqlserver-db-access-hardened-2026-10-14.json)은 개발 실행기와 운영 SP·격리 수준 검증을 포함한다. 실행별 통과 수·실제 엔진·이미지·정리 상태는 JSON에 기록한다. 초기 보고서는 당시 한계의 근거로 보존한다.

[2026-10-14 비상 중단 추가 결과 JSON](../../../../docs/verification/sqlserver-db-emergency-stop-2026-10-14.json)은 앞의 검사와 비상 중단 DB 수단 검증을 포함한다. `emergency_stop.py`의 관리자는 임시 sa로 모사하며 고정 테스트 세션만 종료한다. 이 코드를 운영 KILL 도구로 배포하지 않는다. 이유: 사용자 인증·최소권한 제어·SPID 재사용 경쟁·장애 복구는 별도 구현이 필요하다. [사용자 긴급 중단 계약](../../../../docs/production-db-emergency-stop.md).

[2026-10-14 중앙 제어 추가 결과 JSON](../../../../docs/verification/sqlserver-db-coordination-2026-10-14.json): 총 114개 기대 결과 일치. `coordination.py`는 하나의 중앙 SQLite 원장과 실제 sqlcmd 세션을 연결해 미승인 접속 거부·에이전트/DB 간 전역 슬롯·독립 stop CLI·오류/timeout 취소·서버 종료 확인·명시적 복구를 검사한다. 사용자 인증은 fixture-human으로 모사하며 이 adapter 역시 Docker 전용이다.
