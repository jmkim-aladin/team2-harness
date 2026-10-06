# OpenHands 로컬 1차 시험 — 2026-09-28

- 설치: Agent Canvas 1.24.0, Agent Server 1.49.6, uv 0.12.19. 설치 폴더는 `/private/tmp/team2-openhands-pilot-20260928`이며 임시 저장소다.
- 결과: Canvas HTTP 200, 응답 HTML의 통계 비활성화 플래그 확인. 실제 브라우저 조작 시험은 하지 않았다.
- OS 제한: 외부 네트워크 차단, 시험용 loopback 포트만 허용, 사용자 홈 읽기 차단, 쓰기는 시험 폴더만 허용, Mach IPC는 사용자 경로 확인용 서비스만 허용.
- 차단 시험: 허용 서버 GET 성공, 차단 서버 GET/POST/PUT/PATCH/DELETE 및 셸·Node 자식 호출 실패, 차단 서버 수신 0건. `verify_boundary.py`로 재현한다. 전체 권한 우회 감사를 뜻하지 않는다.
- 초기 실패와 해결: browser-use 화면 조회에서 abort. 설치본의 브라우저 도구 등록 4곳을 제외한 로컬 패치와 공식 `OH_PRELOAD_TOOLS=false` 설정을 함께 적용해 기동 성공. 패치는 `disable-browser.patch`이며 패키지 재설치 시 다시 적용해야 한다. 공식 무수정 배포판의 기본 기동 성공으로 해석하지 않는다.
- 미검증: 실제 모델 로그인, 하네스 적용, 대화 재개·독립 리뷰, MCP 경로, 재시작 후 차단·기록 보존.
- 현재 실행 중: http://127.0.0.1:18760 (Canvas), 127.0.0.1:18763 (Agent Server). Safari 에이전트 선택 화면 확인. 기존 인증·실제 티켓·실제 DB를 연결하지 않았고 자동화 서버도 시작하지 않았다.
- 임시 런타임 제거 시 다시 설치가 필요하다. 잠금 파일은 `package-lock.json`에 보존했다. 로컬 시험 API 키는 이 폴더에 복사하지 않았다.

실행 관리: `python3 .artifacts/openhands-pilot-20260928/manage.py start|stop|status`. 다음 단계는 회사 모델 계정의 인증 경로와 모델 통신을 제한적으로 연결하는 것이다. 현재 외부 모델 통신은 차단돼 있으며 실제 AI 응답은 미검증이다.
