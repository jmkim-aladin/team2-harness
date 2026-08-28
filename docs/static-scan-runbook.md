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
| `partner-integration-batch` | Kotlin / Spring | Sonar + Fortify | 동일 |
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

### Windows 실행으로 메워진 C# 공백 (2026-07-29 서버 실측)

| projectKey | macOS 언어 분포 | Windows 실행 후 | ncloc |
|---|---|---|---|
| `max-api` | `xml=2651` (C# 0줄) | **`cs=17789`**;xml=433 | 2,651 → **18,222** |
| `tobe` | `css/js/web/xml` (C# 0줄) | **`cs=43623`**;css=71992;js=121734;web=19906;xml=4213 | 212,899 → **261,577** |
| `maxcms-api` | `cs=10708` (정상) | `cs=10802`;docker=54;shell=6 | 10,768 → 10,862 |

6개월간 SAST 공백이던 C# 약 1,000파일이 처음으로 분석됐다.

## 사전 조건

### 공통

- git
- SonarQube 사용자 토큰 (`scan` + `provisioning` 글로벌 권한). `provisioning`이 있으면 신규 프로젝트가 스캔 시 자동 생성된다.
- 스캔 대상 repo가 로컬에 clone돼 있어야 한다. 러너는 `git worktree`로 기준 브랜치를 별도 체크아웃하므로 **현재 체크아웃 브랜치나 uncommitted 변경은 건드리지 않는다.**

#### Fortify SSC FPR 업로드 토큰

- SSC URL: 로컬 `FORTIFY_SSC_URL` 환경변수로 관리하며 내부 주소를 공개 저장소에 기록하지 않는다
- 서버 API 버전: `25.4.0.0137`
- 토큰 종류: 최소 권한인 `AnalysisUploadToken`
- Keychain/Credential Manager 이름: `fortify-ssc-analysis-upload-token`

Firefox에서 SSC에 로그인한 뒤 `Administration > Users > Token Management > NEW`로 이동해
`AnalysisUploadToken`을 생성하고, 한 번만 표시되는 **encoded token**을 복사한다. 토큰 값은 채팅,
위키, 티켓, `.env`, `settings.json`, 셸 인자에 넣지 않는다.

하네스 루트의 실제 터미널에서 다음 명령을 실행해 마스킹 프롬프트에 토큰 값을 붙여넣는다.
`tools/cred.py set`은 값을 명령줄 인자로 받지 않으므로 셸 히스토리에 남기지 않는다.

```bash
python3 tools/cred.py set fortify-ssc-analysis-upload-token
python3 tools/cred.py check fortify-ssc-analysis-upload-token
```

두 번째 명령은 존재 여부만 확인하며 값을 출력하지 않는다. 자동화에서는 필요한 순간에만 값을
캡처하고 사용 직후 해제한다.

```bash
SSC_TOKEN="$(python3 tools/cred.py get fortify-ssc-analysis-upload-token)"
curl --config - <<EOF
fail-with-body
proto = "=https"
header = "Authorization: FortifyToken $SSC_TOKEN"
url = "$FORTIFY_SSC_URL/api/v1/projectVersions?limit=1"
EOF
unset SSC_TOKEN
```

인증 헤더를 `curl -H` 인자로 직접 넘기지 않는다. 위 패턴은 토큰을 프로세스 인자(`ps`)에
노출하지 않고 표준 입력으로만 전달한다. 셸 xtrace(`set -x`)가 켜져 있으면 먼저 끈다.

FPR은 대상 Application Version ID를 확인한 뒤
`POST /ssc/api/v1/projectVersions/{versionId}/artifacts`에 `multipart/form-data`의 `file` 필드로
등록한다. 토큰과 업로드 절차의 SoT는 SSC 서버의 `/html/docs/overview`와
`/html/docs/api-reference`다.

##### 월별 FPR 일괄 등록

`scripts/upload-fortify-fprs.py`는 디렉터리의 `*.fpr`을 SSC 애플리케이션에 매핑하고 다음을 수행한다.

1. 대상 Application Version(예: `26.08`)이 이미 있으면 **버전 생성과 FPR 업로드를 모두 건너뛴다**.
2. 없으면 가장 최근 버전의 속성·분석 처리 규칙·버그 트래커 설정·커스텀 태그를 복사해 새 버전을 커밋한다.
3. 새 버전에만 FPR을 업로드하고 `PROCESS_COMPLETE` 또는 `REQUIRE_AUTH`까지 상태를 확인한다.
4. `REQUIRE_AUTH`는 업로드 실패가 아니라 SSC 처리 규칙에 따른 승인 대기다. 스크립트가 자동 승인하지 않는다.

파일명은 대소문자·하이픈과 `-server`/`-web` 접미사를 정규화해 매칭한다. 팀 고유 예외는
`partner-integration-batch.fpr -> B2B Batch` 하나이며, 명백한 근접 오타(`Bazzar`/`Bazaar`)만
후보 점수와 단일성 검사를 통과할 때 보정한다. 모호한 매칭은 업로드하지 않고 실패한다.

새 버전 생성에는 광범위하지만 24시간 이내 단기 작업용인 `UnifiedLoginToken`이 필요하다.
SSC UI에서 만료를 짧게 지정해 **encoded token**을 만들고 다음 이름으로 로컬 금고에 저장한다.
이 토큰은 일시적이므로 `harness.manifest.json`의 상시 필수 자격증명에는 넣지 않는다.

```bash
python3 tools/cred.py set fortify-ssc-unified-login-token
```

매월 `YYYYMM`만 명시한다. 기본 FPR 루트는 `~/Documents/Work/fortify`이며, 예를 들어
`--month 202609`는 디렉터리 `~/Documents/Work/fortify/202609`와 SSC 버전 `26.09`로 변환된다.
항상 dry-run으로 매핑과 SKIP/CREATE 대상을 먼저 확인한 뒤 같은 명령에 `--apply`를 붙인다.

```bash
export FORTIFY_SSC_URL='https://<ssc-host>/ssc'
python3 scripts/upload-fortify-fprs.py --month 202609
python3 scripts/upload-fortify-fprs.py --month 202609 --apply
```

SSC가 아직 HTTP만 제공한다면 토큰 탈취 위험이 있으므로 HTTPS 전환을 우선 요청한다. 불가피하게
격리된 신뢰 경로에서 실행할 때만 매 호출에 `--allow-insecure-http`를 붙여 예외를 명시한다.

기본 루트가 아닌 곳에서 실행할 때는 `--root`를 사용한다. 비정기 버전은 기존의 명시적 인자를 쓴다.

```bash
python3 scripts/upload-fortify-fprs.py \
  --directory ~/Documents/Work/fortify/202608 \
  --version 26.08
```

완료 후 `UnifiedLoginToken`은 SSC Token Management에서 revoke하고 로컬 Keychain에서도 제거한다.
`AnalysisUploadToken`은 다음 월 등록에 재사용할 수 있지만, 팀원 간 공유하지 않는다.

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
| SonarScanner CLI | TS/JS·Kotlin·T-SQL | `sonar-scanner.bat`가 PATH에 있어야 한다. `-windows-x64` 배포본은 JRE를 번들하므로 별도 Java 설치가 필요 없다 |
| `dotnet-sonarscanner` | .NET 8 SDK-style (`maxcms-api`) | `dotnet tool install --global dotnet-sonarscanner`. `%USERPROFILE%\.dotnet\tools`가 PATH에 있어야 한다 |
| **SonarScanner for MSBuild** | .NET Framework legacy (`max-api`·`tobe`) | `sonar-scanner-msbuild-<ver>-**net-framework**` 배포본의 `SonarScanner.MSBuild.exe`. .NET Core flavor는 legacy csproj를 처리하지 못한다. 실행 시 "Using the .NET **Framework** version"이 찍히는지 확인해라 |
| Visual Studio Build Tools 2022 | MSBuild + .NET Framework 4.8 targeting pack | 러너가 `vswhere.exe`로 자동 탐지한다 |
| `nuget.exe` | NuGet 복원 | `MSBuild.exe`는 `dotnet` CLI와 달리 **자동 복원을 하지 않는다.** packages.config뿐 아니라 SDK-style(PackageReference)도 복원이 선행돼야 컴파일된다. 러너는 msbuild 모드에서 항상 복원한다 |
| Fortify SAST | Fortify 스캔 | `FORTIFY_HOME` 환경변수로 설치 경로 지정. **설치 디렉토리명이 배포본에 따라 다르다** — 실측 설치본은 `OpenText_SAST_Fortify_26.2.0`이고 이전 기본값 `Fortify_SCA_26.2.0`가 아니었다 |
| **Fortify 룰팩** | Fortify `-scan` 단계 | **설치본에 룰팩이 들어 있지 않다.** `$FORTIFY_HOME\Core\config\rules`에 `README.TXT`만 있으면 미설치다. 룰팩 zip(예: `2026Q2`)의 `rules\*.bin`(37개·14MB)과 `ExternalMetadata\externalmetadata.xml`를 해당 경로로 복사해라. 없으면 translate는 되고 scan에서 `[error]: No rules files found`로 실패한다 |
| **.NET 10 런타임** | Fortify C# / VB.NET 번역 | Fortify 26.2.0의 `dotnet-translator`는 **net10.0 대상**이라 `Microsoft.NETCore.App 10.0.0`이 필요하다. .NET 8·9만 있으면 번역기가 실행되지 못해 **`.cs` 0건 번역**이 된다. `dotnet --list-runtimes`로 10.x 존재를 확인해라 |

**PowerShell 버전 주의 (필수)**: 러너는 Windows PowerShell 5.1에서도 동작하지만, `.ps1`이 **BOM 없는 UTF-8**이면 5.1이 파일을 ANSI(한국어 환경 CP949)로 읽어 한글이 깨지고 파싱이 실패한다. `run-static-scan.ps1`은 이 때문에 **UTF-8 BOM을 유지해야 한다.** 편집기가 BOM을 떼면 다음으로 확인한다.

```powershell
$e=$null
[System.Management.Automation.Language.Parser]::ParseFile("$PWD\scripts\run-static-scan.ps1",[ref]$null,[ref]$e) | Out-Null
if($e){ $e | ForEach-Object { "line $($_.Extent.StartLineNumber): $($_.Message)" } } else { 'parse: OK' }
```

에러가 한글 깨짐과 함께 나오면 문법 오류가 아니라 인코딩 문제다. BOM을 붙이면 해소된다.

토큰 저장 (DPAPI, 현재 Windows 사용자 계정 전용):

```powershell
.\scripts\run-static-scan.ps1 -SaveToken
```

`%LOCALAPPDATA%\team2\sonarqube-token.dpapi`에 암호화 저장된다. 다른 사용자·다른 머신에서는 복호화되지 않는다. **repo에 커밋하지 마라.**

대상 repo clone은 `scripts/clone-catalog-repos.ps1`로 할 수 있다. 이 스크립트는 `AASM`을 `workspace\s3manager`에 두므로(다른 repo는 러너 레이아웃과 일치) 러너가 `AASM`·`s3manager` 두 경로를 모두 탐색한다.

워크스페이스 경로가 `%USERPROFILE%\Documents\workspace`와 다르면:

```powershell
$env:TEAM2_WORKSPACE_PATH = 'D:\workspace'
```

## 실행

```bash
# macOS
./scripts/run-static-scan.sh --dry-run all      # 실행 계획만
./scripts/run-static-scan.sh all
./scripts/run-static-scan.sh aasm max-front     # 특정 repo
./scripts/run-static-scan.sh partner-integration-batch # B2B 배치 월례 점검
./scripts/run-static-scan.sh svc:max            # max 서비스 전체
./scripts/run-static-scan.sh --sonar-only all
./scripts/run-static-scan.sh --fortify-only tobe
```

```powershell
# Windows
.\scripts\run-static-scan.ps1 -Target all -DryRun
.\scripts\run-static-scan.ps1 -Target all
.\scripts\run-static-scan.ps1 -Target aasm,max-front
.\scripts\run-static-scan.ps1 -Target partner-integration-batch
.\scripts\run-static-scan.ps1 -Target svc:max
.\scripts\run-static-scan.ps1 -Target all -SonarOnly
```

**실행 위치 주의 (Windows 실측 2026-07-29)**: Sonar 단계는 **실제 콘솔이 있는 포그라운드**에서 돌려야 한다. `dotnet-sonarscanner`·`SonarScanner.MSBuild`는 콘솔 없는 분리 프로세스(`Start-Process -WindowStyle Hidden` 등)에서 아무 메시지도 남기지 않고 죽는다(3회 재현). Fortify는 영향이 없다.

`tobe`처럼 오래 걸리는 대상은 단계를 나누는 것이 안정적이다.

```powershell
# 1) Sonar — 포그라운드 (repo당 약 3분)
.\scripts\run-static-scan.ps1 -Target tobe -SonarOnly

# 2) Fortify — 분리 실행 (빌드·번역 약 14분 + scan)
Start-Process powershell -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-Command',
  "`$env:FORTIFY_HOME='C:\Program Files\Fortify\OpenText_SAST_Fortify_26.2.0'; .\scripts\run-static-scan.ps1 -Target tobe -FortifyOnly") `
  -RedirectStandardOutput .\tobe-fortify.log -WindowStyle Hidden
```

**진행 판단**: 부모 `java`의 CPU가 0이어도 정체가 아니다. `aspcodegen.exe` / `dotnet-translator.exe`의 CPU 증가량을 봐라 (아래 함정 표 참조).

**대상 해석 규칙**: repo 키가 서비스명보다 우선한다. `tobe`는 repo(`tobe/Tobe`)로 해석되므로 tobe 서비스 전체는 `svc:tobe`를 써야 한다.

**기준 브랜치**: `origin/main`이 있으면 main, 없으면 `origin/master`. develop은 쓰지 않는다 (팀 결정 2026-07-29).

`partner-integration-batch`는 repo의 Gradle `sonar` task가 테스트와 JaCoCo XML 생성을 함께 실행한다. 기존 SonarQube 커버리지 이력을 보존하려면 공통 CLI가 아니라 `gradle` 모드를 사용해야 한다. 기준은 GitHub 기본 브랜치인 `origin/main`이며, 로컬 checkout을 전환하지 않고 러너의 fetch + 임시 worktree 경로를 사용한다.

Gradle Sonar plugin 7.2의 `sonarResolver`는 `SONAR_TOKEN` 환경변수만으로 인증되지 않는다(401 실측). 러너는 `scripts/sonar-token.init.gradle`을 통해 환경 토큰을 JVM property에 연결한다. init script에는 토큰 값이 없고, 토큰을 argv·repo 파일에 남기지 않는다.

**예외 1건 — `tobe`는 `origin/develop`** (사용자 결정 2026-07-29). `tobe`의 `origin/main`(2026-01-16)은 **실제로 컴파일되지 않는다**: `Aladin.Tobe.Bll\Search\SearchEngine.cs(582,32) error CS0103: 'isInternal'`. develop 대비 565커밋 뒤이고 develop에서는 해당 참조가 없어 빌드가 통과한다. C# 분석은 빌드 성공이 전제이므로 main으로는 596파일을 Roslyn·Fortify 어느 쪽으로도 분석할 수 없다. 나머지 10 repo는 규칙 그대로다.

`max-api`는 예외가 아니다. 처음 main 빌드가 깨진 원인은 브랜치가 아니라 `Configuration`이었고(`Web.Debug.config` 부재), `/p:Configuration=Release`로 `origin/main` 빌드가 통과한다.

**보고 시 주의**: 러너는 `sonar.branch.name`을 넘기지 않으므로 develop 코드가 프로젝트 기본 브랜치 슬롯에 올라간다. `tobe`의 기존 이력은 main 기반이라 이번 분석부터 기준이 바뀐다. leak period·New Code 산정에 영향이 있으니 보고서에 명시해야 한다. 러너가 `git fetch` 후 `git worktree`로 해당 ref를 별도 디렉토리에 꺼내 스캔하고, 끝나면 제거한다. Ctrl-C로 중단해도 trap이 정리한다.

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

**게이트 2의 Windows 보강 (2026-07-29)**: .NET msbuild 모드는 C#을 빌드 통합으로 번역하므로 레지스트리 `Globs`에 `.cs`가 없다. 그러면 분모가 0이 되고, 예전 코드는 그때 커버리지를 100%로 떨어뜨렸다. 그 결과 **한 파일도 번역되지 않은 스캔이 `OK / 커버리지 100%`로 통과했다** (실측: `maxcms-api` 번역 0/0, 이슈 0건, FPR에는 번역 오류 기록). 세 가지를 함께 고쳤다.

- 분모에 `**/*.cs`를 포함한다 (프론트 자산 `Globs`가 있으면 합친다)
- 번역 파일 0건은 **FAIL**로 내린다. "이슈 0건"은 깨끗한 것이 아니라 보지 않은 것이다
- 분자도 분모와 같은 확장자만 센다. `-show-files`는 `.csproj` 등 분모에 없는 파일까지 세어 100%를 넘겼고(실측 `206/201 = 102%`), 그 상태로는 ".cs 100 + 기타 106"도 102%로 보여 실제 누락을 가린다

**빌드 통합 번역의 전제**: Fortify는 **실제로 컴파일되는 파일만** 번역한다. 증분 빌드면 번역 대상이 0이 된다(실측: 재실행 시 `files=0`). `/t:Rebuild`와 NuGet 복원이 함께 있어야 성립한다.

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

### Windows 실측 함정 (2026-07-29 최초 Windows 실행에서 확인)

macOS `.sh`에는 없고 Windows PowerShell 판에만 있는 문제들이다. 전부 러너에서 수정했다.

| 증상 | 원인 | 대응 |
|---|---|---|
| 파싱 오류 21건, 메시지에 한글 깨짐 | BOM 없는 UTF-8을 PS 5.1이 CP949로 디코딩 → 깨진 바이트가 따옴표·백틱으로 해석 | `.ps1`에 UTF-8 BOM 유지. 문법 오류가 아니다 |
| 스캐너가 정보성 메시지 한 줄 출력하고 스크립트 즉사 (rc=0인데도) | PS 5.1은 `*>>`로 리다이렉트한 네이티브 stderr를 `NativeCommandError`로 감싸고, 전역 `$ErrorActionPreference='Stop'`이 이를 종료 오류로 만든다 | 네이티브 호출 함수에 함수 스코프 `$ErrorActionPreference='Continue'`. 성공 판정은 `$LASTEXITCODE`로 한다 |
| 정리 루틴이 죽어 worktree가 등록된 채 남음 | 같은 원인. `git worktree remove`의 경고 한 줄에 `Remove-Worktree`가 사망 | 정리 함수도 `Continue`로 낮춤 |
| 게이트 1·3·4가 아무것도 못 잡음 (로그 검색 전부 실패) | PS 5.1의 `>`/`>>`/`*>>`는 Out-File 기반이고 기본 인코딩이 **UTF-16LE**. UTF-8 헤더 뒤에 UTF-16 본문이 붙어 `Select-String`이 매칭 실패 | 스크립트 앞부분에 `$PSDefaultParameterValues['Out-File:Encoding']='utf8'` |
| `max-api`·`tobe`가 스캔되지 않았는데 종료 코드 0 | `Set-StrictMode -Version Latest`에서 없는 키(`$Cfg.Globs`) 접근 시 `PropertyNotFoundStrict` 예외 → 루프 중단. 런처의 `$LASTEXITCODE`는 직전 네이티브 명령 값(0)이 남음 | 키 존재 확인 후 접근. 래퍼에서 예외를 명시적으로 잡아 성공과 구분 |
| Fortify가 `번역 0/0 (100%)`로 **OK** 판정 | msbuild 모드는 `Globs`가 없어 분모가 0이 되고, 코드가 그때 `pct=100`으로 떨어뜨렸다 | 분모에 `**/*.cs` 포함. 번역 0건은 FAIL. 분자도 분모와 같은 확장자만 센다 |
| `-FortifyOnly`로 돌리면 Fortify C# 번역 0건 | 도구 탐지가 `$needSonar` 블록 안에만 있어 `$MsBuildExe`가 `$null` → `sourceanalyzer`가 솔루션·스위치를 '번역할 파일'로 취급 (FPR에 `[101] File t:Rebuild not found`) | MSBuild·nuget 탐지를 `$needSonar` 밖으로 이동. `$MsBuildExe`가 없으면 즉시 FAIL |
| `.cs` 0건 번역, FPR에 `[1103] Translator execution failed` | Fortify `dotnet-translator`가 net10.0 대상인데 .NET 10 런타임 부재 | .NET 10 런타임 설치 (위 사전 조건 표) |
| scan 단계 `[error]: No rules files found` | 룰팩 미설치 | 룰팩 복사 (위 사전 조건 표) |
| `Web.Debug.config 파일을 찾을 수 없다` 로 빌드 실패 | `max-api`·`tobe`에 `Web.Debug.config`가 없는데 MSBuild 기본값이 `Configuration=Debug`라 `TransformWebConfig` 타겟이 실행됨. **`/p:TransformWebConfigEnabled=false`로는 회피되지 않는다(실측 반증)** | `/p:Configuration=Release` 지정. 두 repo 모두 `Web.Release.config`가 있다 |
| Fortify 번역 파일 수가 0 또는 예상보다 훨씬 적음 (빌드 통합 모드) | Fortify 빌드 통합 번역은 **실제로 컴파일되는 파일만** 잡는다. 증분 빌드면 번역 대상이 없다 | `/t:Rebuild` 유지. NuGet 복원도 선행돼야 한다 |
| 백그라운드로 띄운 러너가 CPU 0%로 무한 대기 | 부모 셸이 먼저 종료되어 자식이 상속한 출력 핸들에 쓰다가 블록 | 포그라운드 실행, 또는 `Start-Process -RedirectStandardOutput`으로 부모와 분리(파일 핸들은 파이프처럼 차지 않는다) |
| **콘솔 없는 분리 프로세스에서 SonarQube 단계가 조용히 죽는다** (로그 5바이트, 오류 메시지 없음, 예외도 없음) | `dotnet-sonarscanner`·`SonarScanner.MSBuild`는 `Start-Process -WindowStyle Hidden` 처럼 콘솔이 없는 환경에서 실패한다. Fortify(`sourceanalyzer`)는 영향 없다. 실측 3회 재현 | **Sonar 단계는 포그라운드(실제 콘솔)에서 돌려라.** 장시간 Fortify만 분리 실행한다. 실무 조합: `-SonarOnly`를 포그라운드로, `-FortifyOnly`를 `Start-Process`로 |
| **`tobe` Fortify가 멈춘 것처럼 보인다** (부모 java CPU 0, 로그 정지, FPR 미생성이 수십 분) | **오진하기 쉬운 정상 동작이다.** `Aladin.ToBe.Web` 번역 단계에서 자식 `aspcodegen.exe`(ASP.NET 뷰 코드 생성, web≈20k ncloc)가 **단일 스레드로 코어 하나를 100%** 쓰며 오래 돌고, 부모 java는 자식을 기다려 유휴로 보인다. 로그도 이 구간에서 출력이 없다 | **죽이지 마라.** 진행 여부는 부모가 아니라 `aspcodegen.exe` / `dotnet-translator.exe`의 **CPU 증가량**으로 판단해라. 실측 2026-07-29: 정상 진행 중인 실행을 정체로 오판해 두 번 중단시켰다 |

### 공통 함정

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

- **보고서 md/PDF**는 6월엔 수작업이었다
- **KB 업로드** — DEV2-6427이 참조하는 `fortify-upload-kb.py`가 현재 머신에 없다

**정정 (2026-07-29, Windows 실측)**: "developer workbook PDF 생성 도구가 없다"는 macOS 설치본 기준이었고 Windows 머신에는 **도구가 있다.** SCA 설치본(`OpenText_SAST_Fortify_26.2.0`)과 별개로 도구 번들이 설치돼 있다.

```
C:\Program Files\Fortify\OpenText_Application_Security_Tools_25.4.0\bin\
  auditworkbench.cmd        ← Audit Workbench
  BIRTReportGenerator.cmd   ← BIRT 리포트
  ReportGenerator.bat       ← 리포트 생성
  scancentral.bat, fortifyclient.bat, CustomRulesEditor.cmd, ScanWizard.cmd
```

즉 P2의 워크북·보고서 PDF 경로는 조달이 아니라 **연결 작업**이다. SCA(26.2.0)와 도구 번들(25.4.0) 버전이 다르니 FPR 호환성은 확인이 필요하다.

P2(월례 스케줄 + 보고서 자동 생성) 범위에서 이 경로를 확보해야 한다.

## 관련 문서

- 티켓 컨텍스트·결과 이력: Obsidian vault `wiki/processes/tickets/dev2-7594.md`
- 스프린트 마감 절차의 정적 점검 항목: [docs/sprint/sprint-closing-process.md](./sprint/sprint-closing-process.md)
- 로컬 자격증명 정책: [policies/local-credentials-policy.md](../policies/local-credentials-policy.md)
- 서비스 프로파일: [catalog/](../catalog/)
