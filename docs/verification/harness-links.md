# DEV2 하네스 링크 동기화 실행 검증 계약

실제 `tools/sync_harness_links.py`의 CLI를 임시 하네스·위키 fixture에서 실행한다. [서비스 공통 계약](../../templates/service-harness/VERIFICATION.md.tmpl)의 CLI 적용 사례이며, 서비스 앱 전체나 사용자 위키의 정합성을 검증하는 계약은 아니다.

## 실행과 대상 확인

- 표면: Python CLI의 `--target services`, 기본 dry-run과 `--apply`
- 필요 환경: Python 3, `git`, 읽을 수 있는 `tools/sync_harness_links.py`
- 시작·준비: 장기 프로세스 없음. helper가 생성한 임시 vault에만 git 저장소를 초기화한 뒤 실행
- 대상 확인: helper가 실행하는 소스의 절대 경로·SHA-256, Python·OS, 실행 시점을 `result.json`에 기록
- 격리: 매 실행의 독립 임시 catalog·vault·git index. 실제 팀 카탈로그·사용자 위키·외부 API를 사용하지 않음

repo 루트에서 실행한다. `--output`은 아직 없는 경로여야 하며 기존 증거를 덮어쓰지 않는다.

```bash
python3 tools/verify_harness_links.py --output /tmp/team2-links-proof-01
```

종료 코드: `0`은 관찰된 기능 검사 통과, `1`은 기대 동작 불일치, `2`는 실행 불가·환경 막힘·잘못된 인자다. 소스 실행이 실패하면 검사 완료로 보고하지 않는다.

## 기능별 검증

| 기능 | 실제 사용자 경로 | 기대 상태 | 증거 |
|---|---|---|---|
| dry-run | `sync_harness_links.py --vault … --harness … --target services` | vault 파일·git 상태의 바이트 해시 불변 | `dry-run.*.txt`, `result.json` |
| 서비스 정보 동기화 | 같은 명령에 `--apply` | 카탈로그의 이름·분류·오너가 문서에 나타남, 예전 정보 제거 | `before.md`, `after.md`, `apply.*.txt` |
| 사람이 쓴 내용 보존 | 같은 apply 경로 | 생성 블록 밖 본문과 별도 사용자 파일 보존 | `after.md`, 검사 결과 |
| 반복 실행 | 같은 apply 재실행 | 생성 블록 중복 없이 같은 문서, `unchanged` 보고 | `repeat.*.txt` |
| 관리 영역 없는 문서 | 생성 마커 없는 문서에 apply | 사용자 문서를 수정하지 않고 `skipped` 보고 | `unmanaged.*.txt` |
| 재개 | 입력 문서를 초기 상태로 돌려 apply | 이미 실행했던 작업도 같은 결과로 수렴 | `resume.*.txt` |

helper는 결과 문서의 실제 값과 파일 해시를 확인한다. 성공 문자열이나 종료 코드 0만으로 통과시키지 않는다. 장기 서버·포트·인증·UI 상태가 없으므로 해당 확인은 이 CLI 사례에 적용하지 않는다.

## 증거와 정리

매 명령의 argv·종료 코드·stdout·stderr, 전후 문서, 원본 소스 digest와 파일별 증거 digest를 기록한다. 실행 중 코드가 바뀌면 통과하지 않는다. 임시 fixture는 성공·실패 모두 정리하고, 증거 디렉터리는 보존한다. `GIT_*` 환경변수의 외부 저장소 우회도 child 환경에서 제거한다.

```bash
python3 -c 'import json,pathlib; p=pathlib.Path("/tmp/team2-links-proof-01/result.json"); r=json.loads(p.read_text()); print(r["status"], r["cleanup"]); print((p.parent/"after.md").read_text())'
```

`cleanup.scratch_removed`와 남은 증거를 확인한다. helper가 만들지 않은 프로세스·경로는 정리하지 않는다. 실제 도구의 `--apply`는 임시 git index에 stage도 수행하므로, 실제 위키를 fixture 대신 사용하지 않는다.

## 계약 유지보수

- 문서 내용이 실제 CLI와 다르면 문서 드리프트, 올바른 CLI 동작을 helper가 검사하지 못하면 도구 공백이다.
- 기대값·사용자 본문·dry-run·멱등성 계약이 실제로 깨졌으면 제품 결함이다. PASS를 얻기 위해 기대값을 현재 오류에 맞추지 않는다.
- 보정 뒤 같은 CLI 검증을 재실행한다. 소스 파서의 모든 YAML 형태, team/policies 대상, 실제 위키 데이터는 이 기능 지도에 포함되지 않는다.

## 최초 실행과 회귀 검사

```bash
python3 -m unittest discover -s tests -p 'test_verify_harness_links.py' -v
```

회귀 검사는 실제 CLI를 실행하고, 성공 메시지만 출력하는 가짜 구현을 실패로 분류하며, 실행 실패 시 정리·로그 보존과 기존 증거 덮어쓰기 거부를 확인한다. 적용 시점 실행 근거는 [pstack 적용 기록](../pstack-harness-implementation.md)에 남긴다.
