# 정적 점검 실행 런북 (SonarQube + Fortify)

월례 정적 점검을 `scripts/run-static-scan.sh`(macOS) / `scripts/run-static-scan.ps1`(Windows)로 실행하는 절차다.
관련 티켓: DEV2-7594(월례 점검), DEV2-7591(프로세스 수립), DEV2-6427(AASM 도입 선례).
작업 컨텍스트·결과 이력은 Obsidian vault `wiki/processes/tickets/dev2-7594.md`에 있다.

## 왜 두 플랫폼인가

**macOS에서는 .NET C#을 스캔할 수 없다.** 실측으로 확인된 플랫폼 제약이다.

- SonarQube: C# 분석은 Roslyn 기반 MSBuild 스캐너가 필요하다. `max-api`·`Tobe`는 legacy csproj(`ToolsVersion="15.0"` + `packages.config`)라 `dotnet build`로 빌드되지 않는다.
- Fortify: `.NET translation is only supported on Windows and Linux.` 를 반환하며 `.cs` 파일을 전부 무시한다.

이 제약 때문에 6개월간 커버리지 공백이 있었다. 2026-07-29 서버 언어 분포 실측:

```
max-api   xml=2651                                → C# 400파일이 한 번도 분석된 적 없음
tobe      css=71779;js=119359;web=17527;xml=4145  → C# 596파일 미분석
```

Docker로 우회는 불가하다. Windows 컨테이너는 macOS에 Windows 커널이 없어 원천 불가이고, QEMU 기반 Windows-in-Docker는 컨테이너에 `/dev/kvm`이 노출되지 않아 가속 없이 돌아간다.

## 플랫폼별 커버리지

| repo | 스택 | macOS | Windows |
|---|---|---|---|
| `aasm` | Next.js / TS | Sonar + Fortify | 동일 |
| `naru-server` | Kotlin / Spring | Sonar + Fortify | 동일 |
| `max-server` | Kotlin (전환용) | Sonar + Fortify | 동일 |
| `max-front` | Next.js / TS | Sonar + Fortify | 동일 |
| `maxcms-front` | Next.js / TS | Sonar + Fortify | 동일 |
| `max-db-script` | T-SQL | Sonar + Fortify | 동일 |
| `tobe-db-script` | T-SQL | Sonar + Fortify | 동일 |
| `maxcms-api` | .NET 8 | Sonar만 (**Fortify SKIP**) | **Sonar + Fortify** |
| `max-api` | .NET FW 4.8 | **양쪽 SKIP** | **Sonar + Fortify** |
| `tobe` | .NET FW 4.8 + JS/CSS | 프론트 자산만 (**C# 제외**) | **C# 포함 전체** |

→ **월례 점검은 Windows에서 돌리는 것이 정답이다.** macOS는 .NET 3건이 공백으로 남는다.

## 사전 조건

### 공통

- git
- SonarQube 사용자 토큰 (`scan` + `provisioning` 글로벌 권한). `provisioning`이 있으면 신규 프로젝트가 스캔 시 자동 생성된다.
- 스캔 대상 repo가 로컬에 clone돼 있어야 한다. 러너는 `git worktree`로 기준 브랜치를 별도 체크아웃하므로 **현재 체크아웃 브랜치나 uncommitted 변경은 건드리지 않는다.**

### macOS

```bash
brew install sonar-scanner
# Fortify SAST 26.2.0 설치 (기본 경로: ~/Applications/Fortify/SAST_26.2.0)
# .NET 8 대상(maxcms-api)이 포함되면:
dotnet tool install --global dotnet-sonarscanner --arch arm64
```

`--arch arm64`가 중요하다. 생략하면 x86_64 apphost가 설치되어 `libhostfxr.dylib is an incompatible architecture`로 실행 자체가 실패한다.

homebrew `dotnet@8`은 apphost 기본 탐색 경로에 런타임을 두지 않는다. 러너가 `dotnet --list-sdks`로 `DOTNET_ROOT`를 자동 탐지하지만, 수동 지정이 필요하면:

```bash
export DOTNET_ROOT=/opt/homebrew/opt/dotnet@8/libexec
```

토큰 저장 (Keychain, 값은 프롬프트로만 입력):

```bash
security add-generic-password -U -a "$USER" -s sonarqube-jmkim-token -w
```

`-w`를 값 없이 써야 대화형 프롬프트가 뜬다. 값을 명령줄에 직접 쓰면 셸 히스토리와 `ps`에 평문으로 남는다.
**반드시 실제 터미널(Terminal.app / iTerm)에서 실행해라.** 에디터나 도구가 감싼 비-TTY 셸에서는 프롬프트가 표시만 되고 입력이 잡히지 않아 빈 값이 저장된다.

### Windows

| 도구 | 용도 | 비고 |
|---|---|---|
| SonarScanner CLI | TS/JS·Kotlin·T-SQL | `sonar-scanner.bat`가 PATH에 있어야 한다 |
| `dotnet-sonarscanner` | .NET 8 SDK-style (`maxcms-api`) | `dotnet tool install --global dotnet-sonarscanner` |
| **SonarScanner for MSBuild** | .NET Framework legacy (`max-api`·`tobe`) | `sonar-scanner-msbuild-<ver>-**net-framework**` 배포본의 `SonarScanner.MSBuild.exe`. .NET Core flavor는 legacy csproj를 처리하지 못한다 |
| Visual Studio Build Tools 2022 | MSBuild + .NET Framework 4.8 targeting pack | 러너가 `vswhere.exe`로 자동 탐지한다 |
| `nuget.exe` | `packages.config` 복원 | legacy repo는 `dotnet restore`로 복원되지 않는다 |
| Fortify SAST | Fortify 스캔 | `FORTIFY_HOME` 환경변수로 설치 경로 지정. 기본값 `C:\Program Files\Fortify\Fortify_SCA_26.2.0` |

토큰 저장 (DPAPI, 현재 Windows 사용자 계정 전용):

```powershell
.\scripts\run-static-scan.ps1 -SaveToken
```

`%LOCALAPPDATA%\team2\sonarqube-token.dpapi`에 암호화 저장된다. 다른 사용자·다른 머신에서는 복호화되지 않는다. **repo에 커밋하지 마라.**

워크스페이스 경로가 `%USERPROFILE%\Documents\workspace`와 다르면:

```powershell
$env:TEAM2_WORKSPACE_ROOT = 'D:\workspace'
```

## 실행

```bash
# macOS
./scripts/run-static-scan.sh --dry-run all      # 실행 계획만
./scripts/run-static-scan.sh all
./scripts/run-static-scan.sh aasm max-front     # 특정 repo
./scripts/run-static-scan.sh svc:max            # max 서비스 전체
./scripts/run-static-scan.sh --sonar-only all
./scripts/run-static-scan.sh --fortify-only tobe
```

```powershell
# Windows
.\scripts\run-static-scan.ps1 -Target all -DryRun
.\scripts\run-static-scan.ps1 -Target all
.\scripts\run-static-scan.ps1 -Target aasm,max-front
.\scripts\run-static-scan.ps1 -Target svc:max
.\scripts\run-static-scan.ps1 -Target all -SonarOnly
```

**대상 해석 규칙**: repo 키가 서비스명보다 우선한다. `tobe`는 repo(`tobe/Tobe`)로 해석되므로 tobe 서비스 전체는 `svc:tobe`를 써야 한다.

**기준 브랜치**: `origin/main`이 있으면 main, 없으면 `origin/master`. develop은 쓰지 않는다 (팀 결정 2026-07-29). 러너가 `git fetch` 후 `git worktree`로 해당 ref를 별도 디렉토리에 꺼내 스캔하고, 끝나면 제거한다. Ctrl-C로 중단해도 trap이 정리한다.

**출력**: `~/Documents/Work/static-scan/<날짜>/`
- `summary-<타임스탬프>.md` — 요약표 + 실패/부분/공백 목록 + repo별 상세
- `<repo>.fpr` — Fortify 결과
- `logs/<repo>.log` — 스캐너 원본 로그

**종료 코드**: `0` 전 대상 완전 스캔 / `2` 공백(SKIP) 또는 부분 결과(PARTIAL) 존재 / `1` 실패

## 결과 해석

### 판정 4종

| 판정 | 의미 | 대응 |
|---|---|---|
| `OK` | 완전 스캔. 오류 없고 번역 커버리지 임계 통과 | 결과 수치를 신뢰해도 된다 |
| `PARTIAL` | 스캔은 끝났으나 결과가 불완전 | **수치를 신뢰하지 마라.** 로그 확인 후 재실행 |
| `SKIP` | 플랫폼 제약으로 실행 불가 | 도구 설정 문제가 아니다. 다른 플랫폼에서 돌려야 한다 |
| `FAIL` | 스캐너 실패 | 로그의 rc와 메시지 확인 |

### 게이트 4개

러너는 "돌았으니 성공"으로 판정하지 않는다. 실측에서 이런 거짓 판정이 실제로 나왔다.

1. **Fortify FPR 오류 검사** — Fortify는 내부 분석 오류가 있어도 FPR을 만들고 `rc=0`을 반환한다. `FPRUtility -information -errors`와 로그의 `results may be incomplete`·`Fatal:`·`Unexpected exception`을 검사해 PARTIAL로 내린다.
   *실측: `aasm.fpr`이 `OK / 13 issues`로 보고됐지만 로그에 `scan results may be incomplete`, `Unexpected exception during structural analysis`, `Fatal: No serialized file`, FPR 오류 code 1011·1152가 있었다.*

2. **번역 커버리지 대조** — translate된 파일 수를 git 추적 파일 수와 비교해 90% 미달이면 PARTIAL.
   *실측: Fortify에 디렉토리(`.`)를 넘기면 소스를 대량 누락한다 (AASM TS 169파일 중 60만 번역, 36%). 명시 글로브로 전환해 98%로 회복했다.*
   *분모는 translate와 같은 제외 규칙을 써야 한다. 안 그러면 거짓 PARTIAL이 난다 (tobe에서 `min.js` 104건이 분모에만 남아 84%로 오판).*

3. **SonarQube CE task 확인** — 업로드 성공 ≠ 서버 반영. `report-task.txt`의 `ceTaskId`로 `api/ce/task`가 `SUCCESS`가 될 때까지 폴링한다.
   *이 확인 없이 measures를 읽으면 기존 프로젝트는 '이전 분석값'을 즉시 돌려주므로 재시도 로직이 무의미해진다.*

4. **심각도 집계 파싱 검증** — `FPRUtility -information -analyzerIssueCounts`는 analyzer 그룹 수이고 심각도가 아니다. `[fortify priority order]:critical|high|medium|low` 쿼리로 센다. 파싱 실패를 0으로 떨어뜨리면 "Critical 0건"이라는 거짓 통과가 나오므로 PARTIAL로 처리한다.

### 원시 건수와 고유 위치를 함께 봐라

Fortify는 데이터플로 경로가 여러 개 수렴하면 **같은 줄을 반복 카운트**한다. 원시 건수만 쓰면 조치 대상이 부풀려진다.

```bash
FU=$FORTIFY_HOME/bin/FPRUtility
$FU -information -listIssues -project x.fpr | grep -E '^\s+\S+:[0-9]+$' | sort -u | wc -l
```

*실측: `tobe` 705건 → 고유 위치 305곳(43%). `max-server`의 `SecretsManagerException.kt:5`는 단독으로 14회 이상 반복됐다.*

### 오탐을 걸러라

repo 전체를 넘기면 매니페스트·픽스처·테스트가 Critical로 잡힌다. `aasm` 15곳 중 실제 조치 대상은 4곳이었고 나머지는 `package-lock.json` 5건, 로컬 픽스처 3건, 테스트 3건이었다.

대응은 두 가지다. ① 레지스트리의 소스 루트 필드(`R_SRCDIRS` / `SrcDirs`)로 스코프를 좁힌다 — `aasm`은 6월 선례대로 `app components lib`로 설정돼 있다. ② repo에 `fortify/scan-filter.txt`를 두고 scan 단계에서 걸러낸다 (`MaxServer`에 선례가 있다). **`-filter`는 scan 단계 인자다. translate에 주면 적용되지 않는다.**

## Quality Gate 주의

기본 게이트는 "Sonar way"이고 New Code 정의는 `PREVIOUS_VERSION`이다. 여기에 함정이 있다.

**`sonar.projectVersion`이 분석 간 동일하면 leak period가 리셋되지 않는다.** 버전이 안 바뀌면 "새 코드"가 첫 분석 이후로 계속 누적된다. 6개월 공백이 통째로 새 코드가 되어 `new_violations`가 37~233까지 올랐다.

러너는 `-Dsonar.projectVersion=<커밋날짜>-<SHA>`를 넘겨 매 분석마다 버전이 바뀌게 한다. 그 결과 new code가 "지난 분석 이후 변경분"으로 정상 산정된다.

**주의**: 첫 분석은 new-code 조건이 실질 평가되지 않아 게이트가 통과한다. 두 번째 분석부터 실패가 드러난다. "1월엔 통과했는데 7월에 실패"는 품질 악화가 아니라 이 구조 때문이다 (`maxcms-api`는 2026-02-02 두 번째 분석에서 이미 ERROR였다).

**커버리지는 규약이므로 지킨다.** "Sonar way"의 새 코드 커버리지 80% 조건을 게이트에서 빼지 않는다. 현재 러너는 테스트를 실행하지 않아 `new_coverage`가 0%다. 새 코드가 생기는 즉시 이 조건으로 실패하므로, 커버리지 리포트 제출 단계를 붙여야 한다.

- `aasm` — `sonar-project.properties`에 `sonar.javascript.lcov.reportPaths` 설정 기존재. 테스트 실행만 붙이면 된다
- `naru-server` — `./gradlew koverHtmlReport`
- 나머지 — 테스트·리포트 경로 조사 선행

팀 기준은 "신규 Critical/High 0건"(DEV2-6427)인데 "Sonar way"는 `new_violations > 0`이면 실패한다. 이 조건 교정은 `gateadmin` 권한이 필요해 보안팀 요청 사항이다 (우리 토큰 권한은 `provisioning`·`scan`·`portfoliocreator`).

## 알려진 함정

| 증상 | 원인 | 대응 |
|---|---|---|
| `dotnet-sonarscanner` 실행 시 `incompatible architecture` | arm64 Mac에 x86_64 apphost 설치 | `--arch arm64`로 재설치 |
| `You must install .NET to run this application` | homebrew dotnet@8이 apphost 기본 경로에 런타임을 두지 않음 | `DOTNET_ROOT` 지정 |
| Fortify scan `not enough memory available` | 힙 부족 | 레지스트리의 힙 필드 상향. `tobe`는 12G로 지정돼 있다. 머신이 한가할 때 재실행 |
| Fortify 번역 파일 수가 예상보다 적음 | 셸이 글로브를 먼저 확장 (bash 3.2에 globstar 없음) | 러너가 `set -f`로 차단한다. 직접 실행 시 글로브를 따옴표로 감싸라 |
| `CE=NO_TASK_FILE` | .NET 스캐너는 `report-task.txt`를 `.sonarqube\out\.sonar\`에 남긴다 | 러너가 두 경로를 모두 탐색한다 |
| T-SQL에서 결과 0건 | T-SQL 분석기 기본 확장자가 `.tsql` | 러너가 `sonar.tsql.file.suffixes=.sql,.tsql` 지정. PL/SQL 충돌을 피해 `plsql`은 `.pks,.pkb`로 밀어둔다 |
| Keychain에 빈 토큰 저장됨 | 비-TTY 셸에서 `security -w` 프롬프트 입력 미수신 | 실제 터미널에서 재실행 |

## 월간 보고 산출물 — 미완

6월 선례(`~/Documents/Work/fortify/report/`)의 산출물은 4종인데 **러너가 만드는 것은 FPR 하나뿐이다.**

```
aasm.fpr → aasm-final.fpr                        (1차 → 수정 후)
aasm-{initial,q3,final}-developer-workbook.pdf   (개발자 워크북)
aasm-fortify-report-2026-06-12.md + .pdf         (보고서)
```

- **developer workbook PDF 생성 도구가 없다.** 현 설치본은 SCA 전용이다. Audit Workbench 미설치, `ReportGenerator`/`BIRTReportGenerator` 바이너리 없음
- **보고서 md/PDF**는 6월엔 수작업이었다
- **KB 업로드** — DEV2-6427이 참조하는 `fortify-upload-kb.py`가 현재 머신에 없다

P2(월례 스케줄 + 보고서 자동 생성) 범위에서 이 경로를 확보해야 한다.

## 관련 문서

- 티켓 컨텍스트·결과 이력: Obsidian vault `wiki/processes/tickets/dev2-7594.md`
- 스프린트 마감 절차의 정적 점검 항목: [docs/sprint/sprint-closing-process.md](./sprint/sprint-closing-process.md)
- 로컬 자격증명 정책: [policies/local-credentials-policy.md](../policies/local-credentials-policy.md)
- 서비스 프로파일: [catalog/](../catalog/)
