<#
.SYNOPSIS
  개발 2팀 정적 점검 원커맨드 러너 (Windows) — DEV2-7594 P1

.DESCRIPTION
  SonarQube + Fortify SAST 스캔을 repo 단위로 순회 실행하고 심각도 요약을 md로 출력한다.
  macOS판 `run-static-scan.sh`와 대상 목록·게이트·종료 코드 계약을 동일하게 유지한다.

  Windows판이 따로 있는 이유는 macOS에서 .NET을 스캔할 수 없기 때문이다.
    - SonarQube: C# 분석은 Roslyn 기반 MSBuild 스캐너가 필요하고 .NET Framework 4.8은
      macOS에서 빌드되지 않는다
    - Fortify: ".NET translation is only supported on Windows and Linux." 를 반환한다
  Windows에서는 두 제약이 모두 사라져 10 repo 전체를 커버한다.

  실측 근거 (2026-07-29, macOS):
    max-api  서버 언어 분포 = xml=2651   → C# 400파일이 한 번도 분석된 적 없음
    tobe     서버 언어 분포 = css/js/web/xml → C# 596파일 미분석

.PARAMETER Target
  all | repo 키 | svc:<서비스>
  repo 키가 서비스명보다 우선한다. `tobe`는 repo(tobe/Tobe)로 해석되므로
  tobe 서비스 전체는 `svc:tobe` 를 쓴다.

.PARAMETER SaveToken
  SonarQube 토큰을 현재 사용자 전용으로 암호화 저장하고 종료한다 (DPAPI).
  값은 프롬프트로 받는다. 인자로 넘기지 않는다.

.EXAMPLE
  .\run-static-scan.ps1 -SaveToken
  .\run-static-scan.ps1 -Target all -DryRun
  .\run-static-scan.ps1 -Target max-api
  .\run-static-scan.ps1 -Target all -SonarOnly

.NOTES
  종료 코드:
    0  전 대상 완전 스캔
    2  완료했으나 커버리지 공백(SKIP) 또는 부분 결과(PARTIAL) 존재
    1  실패 발생 (또는 -FailOnSkip 지정 시 SKIP 존재)

  보안 주의 (축소해 말하지 않는다):
    토큰은 DPAPI로 현재 사용자 계정에 묶여 암호화 저장된다. 그러나 스캐너에 전달되는
    순간 프로세스 인자 또는 환경에 평문으로 존재한다.
      - sonar-scanner CLI      : SONAR_TOKEN 환경변수 (인자 노출 회피)
      - SonarScanner.MSBuild   : /d:sonar.token 인자 필수. 환경변수 미지원 → 노출 잔존
      - Invoke-RestMethod      : 헤더로 전달, 프로세스 인자에는 남지 않음
    같은 계정으로 프로세스 목록을 볼 수 있는 사용자에게는 노출된다.
    단일 사용자 머신 또는 전용 러너를 전제로 한다.
#>

[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [string[]] $Target,

  [switch] $SonarOnly,
  [switch] $FortifyOnly,
  [switch] $DryRun,
  [switch] $KeepWorktree,
  [switch] $FailOnSkip,
  [switch] $SaveToken,

  [string] $OutRoot = (Join-Path $env:USERPROFILE 'Documents\Work\static-scan'),
  [string] $WorkspaceRoot = $(if ($env:TEAM2_WORKSPACE_ROOT) { $env:TEAM2_WORKSPACE_ROOT } else { Join-Path $env:USERPROFILE 'Documents\workspace' })
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Windows PowerShell 5.1의 `>`/`>>`/`*>>` 는 내부적으로 Out-File을 쓰고 기본 인코딩이
# Unicode(UTF-16LE)다. 그러면 스캐너 로그가 UTF-8 헤더 뒤에 UTF-16 본문이 붙은 혼합 파일이 되고
# Select-String이 아무것도 못 찾는다. 게이트 1(FPR/로그 오류)·3(CE task)·4(심각도)가
# 조용히 무력화되어 "경고 0건"이라는 거짓 통과가 난다.
# 실측 2026-07-29: maxcms-api 로그 3.9MB에 NUL 1927개, 'ANALYSIS SUCCESSFUL' 검색 실패.
# 리다이렉션 기본값을 UTF-8로 고정한다. (환경에 따라 UTF-8로 나오기도 해서 수동 테스트만으로는 안 걸린다)
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

# ── 설정 ────────────────────────────────────────────────────────────────────

$SonarHost = 'https://sonarqube.sec.aladin.co.kr'
$TokenFile = Join-Path $env:LOCALAPPDATA 'team2\sonarqube-token.dpapi'
$FortifyHome = if ($env:FORTIFY_HOME) { $env:FORTIFY_HOME } else { 'C:\Program Files\Fortify\Fortify_SCA_26.2.0' }
$FortifyHeapDefault = if ($env:FORTIFY_HEAP) { $env:FORTIFY_HEAP } else { '4G' }

# 테스트 코드 제외 패턴 (2026-07-30 확정, macOS `.sh` 의 TEST_EXCLUDES 와 동일 목록).
#
# 실측 근거: NaruServer는 코드가 1월 이후 한 줄도 안 바뀌었는데 high 4 → 38로 늘었다.
# 1월 스캔이 src/test 를 제외했고 이번 스캔이 포함한 탓이다(38건 중 24건이 src/test).
# 제외 적용 후 kotlin ncloc 20,295 → 15,844 로 1월 값과 정확히 일치했다.
#
# 디렉토리명 기반 `**/test/**` 는 쓰지 않는다. 운영 코드를 버린다:
#   Tobe      Aladin.ToBe.Web\{Views,ViewsReact}\App\Test\**  Applink·Bridge·Device 앱 연동 뷰 12파일
#   max-front src\components\test\**                          AppLinkTest·BridgeTest 등 디버깅 페이지 7파일
# Kotlin은 파일명만으로 부족하다 — TestConfiguration.kt·TestFixtures.kt 가 Test* 접두어라
# `*Test.kt` 에 안 걸린다. src/test/ 경로로 잡는다 (Gradle 규약이라 운영 코드가 없다).
$TestExcludes = @(
  '**/src/test/**','**/src/testFixtures/**','e2e/**','.devops/tests/**'
  '**/cypress/**','**/playwright/**'
  '**/*.test.ts','**/*.test.tsx','**/*.test.js','**/*.test.jsx','**/*.test.mjs'
  '**/*.spec.ts','**/*.spec.tsx','**/*.spec.js','**/*.spec.jsx'
  '**/*Test.cs','**/*Tests.cs'
)

# translate 후 번역 파일 수가 git 추적 파일 수의 이 비율 미만이면 PARTIAL로 본다.
$CoverageThresholdPct = 90

# SonarQube 분석은 서버 큐에서 비동기 처리된다. CE task 완료를 이만큼 기다린다.
$CePollMaxSec = 300
$CePollIntervalSec = 5

# ── 유틸 ────────────────────────────────────────────────────────────────────

function Write-Log  { param([string]$m) Write-Host $m }
function Write-Info { param([string]$m) Write-Host "  $m" }
function Write-Warn { param([string]$m) Write-Host "WARN  $m" -ForegroundColor Yellow }
function Die        { param([string]$m) Write-Host "ERROR $m" -ForegroundColor Red; exit 1 }

# ── 토큰 저장·조회 (DPAPI, 현재 사용자 전용) ────────────────────────────────

function Save-SonarToken {
  $dir = Split-Path $TokenFile -Parent
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  $sec = Read-Host -AsSecureString 'SonarQube 토큰 입력 (화면에 표시되지 않음)'
  if ($sec.Length -eq 0) { Die '토큰이 비어 있다' }
  # ConvertFrom-SecureString은 DPAPI로 현재 사용자 계정에 묶어 암호화한다.
  # 다른 사용자·다른 머신에서는 복호화되지 않는다.
  ConvertFrom-SecureString -SecureString $sec | Set-Content -Path $TokenFile -Encoding ASCII
  Write-Log "저장 완료: $TokenFile"
  Write-Log '이 파일은 현재 Windows 사용자 계정으로만 복호화된다. repo에 커밋하지 마라.'
}

function Get-SonarToken {
  if (-not (Test-Path $TokenFile)) {
    Die "토큰 파일 없음: $TokenFile`n     먼저 실행: .\run-static-scan.ps1 -SaveToken"
  }
  $enc = Get-Content -Path $TokenFile -Raw
  try {
    $sec = ConvertTo-SecureString -String $enc.Trim()
  } catch {
    Die "토큰 복호화 실패. 다른 사용자 계정으로 저장된 파일일 수 있다: $TokenFile"
  }
  # PSCredential 경유가 평문 변수 노출을 가장 짧게 유지한다.
  return ([System.Management.Automation.PSCredential]::new('t', $sec)).GetNetworkCredential().Password
}

function Invoke-SonarApi {
  param([string]$Path)
  $headers = @{ Authorization = "Bearer $script:SonarToken" }
  try {
    return Invoke-RestMethod -Uri "$SonarHost$Path" -Headers $headers -TimeoutSec 30 -Method Get
  } catch {
    return $null
  }
}

# ── repo 레지스트리 ─────────────────────────────────────────────────────────
#
# macOS판과 동일한 대상·순서를 유지한다. Windows에서는 .NET 제약이 없으므로
# SonarMode/FortifyMode가 SKIP 대신 실제 스캐너로 지정된다.
#
#   SonarMode    cli | dotnet | msbuild
#     cli        sonar-scanner CLI (TS/JS, Kotlin, T-SQL)
#     dotnet     dotnet-sonarscanner (.NET 8 이상, SDK-style)
#     msbuild    SonarScanner.MSBuild.exe + msbuild.exe (.NET Framework legacy csproj)
#   FortifyMode  yes | msbuild
#     msbuild    sourceanalyzer -b <id> msbuild /t:Rebuild <sln> (.NET 빌드 통합)
#   SrcDirs      translate 소스 루트 (미지정 시 repo 전체)
#
# 소유권 근거: catalog/max.yaml, catalog/tobe.yaml 의 repos: 주석.
# 타팀 관리(ToBeAndroid·ToBeIos·max-search·Ebook*)와 git repo 아닌 사본은 제외했다.

$GlobsTs      = @('**/*.ts','**/*.tsx','**/*.js','**/*.jsx','**/*.json','**/*.yml','**/*.yaml')
$GlobsKotlin  = @('**/*.kt','**/*.kts','**/*.java','**/*.yml','**/*.yaml','**/*.xml')
$GlobsTsql    = @('**/*.sql')
$GlobsWebFull = @('**/*.js','**/*.jsx','**/*.cshtml','**/*.aspx','**/*.ascx','**/*.config')

$Registry = [ordered]@{
  'aasm' = @{
    # clone-catalog-repos.ps1 은 AASM을 workspace\s3manager 로 clone한다 (macOS 수동 clone은 AASM).
    # 어느 레이아웃이든 동작하도록 대체 경로를 둔다.
    Path = 'AASM'; PathAlt = 's3manager'; Ref = 'origin/main'; SonarKey = 'aasm'
    SonarMode = 'cli'; FortifyMode = 'yes'; Globs = $GlobsTs
    # 6월 선례(DEV2-6294)가 app/components/lib 131파일로 한정했다. repo 전체를 넘기면
    # package-lock.json·tests·docker 픽스처가 Critical로 잡혀 게이트를 막는다 (실측 11/15건).
    SrcDirs = @('app','components','lib')
    Note = 'Next.js/TS. main이 deploy/prod보다 42커밋 뒤'
  }
  'naru-server' = @{
    Path = 'naru\NaruServer'; Ref = 'origin/main'; SonarKey = 'NaruServer'
    SonarMode = 'cli'; FortifyMode = 'yes'; Globs = $GlobsKotlin
    Note = 'Kotlin/Spring. main은 2026-01 이후 정지(개발은 develop)'
  }
  'max-server' = @{
    Path = 'max\MaxServer'; Ref = 'origin/main'; SonarKey = 'MaxServer'
    SonarMode = 'cli'; FortifyMode = 'yes'; Globs = $GlobsKotlin
    ScanFilter = 'fortify\scan-filter.txt'
    Note = 'Kotlin 전환용. scan-filter.txt는 scan 단계 인자로 적용'
  }
  'max-front' = @{
    Path = 'max\max-front'; Ref = 'origin/main'; SonarKey = 'max-front'
    SonarMode = 'cli'; FortifyMode = 'yes'; Globs = $GlobsTs
    Note = 'Next.js 14.2.3/TS'
  }
  'maxcms-front' = @{
    Path = 'max\maxcms-front'; Ref = 'origin/main'; SonarKey = 'maxcms-front'
    SonarMode = 'cli'; FortifyMode = 'yes'; Globs = $GlobsTs
    Note = 'Next.js 14.2.35/TS'
  }
  'maxcms-api' = @{
    Path = 'max\maxcms-api'; Ref = 'origin/main'; SonarKey = 'maxcms-api'
    SonarMode = 'dotnet'; FortifyMode = 'msbuild'
    BuildTarget = 'Aladin.MaxCms\Aladin.MaxCms.sln'
    Note = '.NET 8 SDK-style. macOS에서는 Fortify SKIP이었으나 Windows에서는 커버된다'
  }
  # max-db-script·tobe-db-script 는 점검 대상에서 제외 (2026-07-30 결정).
  # 정의는 남겨 둔다 — -Target max-db-script 로는 여전히 실행 가능하다.
  'max-db-script' = @{
    Path = 'max\max-db-script'; Ref = 'origin/master'; SonarKey = 'max-db-script'
    SonarMode = 'cli'; FortifyMode = 'yes'; Globs = $GlobsTsql
    Note = 'T-SQL. 2026-07-29 신규 생성된 프로젝트'
  }
  'tobe-db-script' = @{
    Path = 'tobe\tobe-db-script'; Ref = 'origin/master'; SonarKey = 'tobe-db-script'
    SonarMode = 'cli'; FortifyMode = 'yes'; Globs = $GlobsTsql
    Note = 'T-SQL. 2026-07-29 신규 생성된 프로젝트'
  }
  'max-api' = @{
    # 기준 브랜치는 규칙대로 origin/main을 유지한다.
    # main 빌드 실패의 원인은 브랜치가 아니라 Configuration이었다 (실측 2026-07-29):
    #   Web.Debug.config가 main·develop 양쪽에 없어서 기본 Configuration=Debug의
    #   TransformWebConfig 타겟이 실패한다. /p:TransformWebConfigEnabled=false 로는 회피되지 않는다.
    #   /p:Configuration=Release 로 origin/main 빌드 클린 확인 (Web.Release.config 존재).
    Path = 'max\max-api'; Ref = 'origin/main'; SonarKey = 'max-api'
    SonarMode = 'msbuild'; FortifyMode = 'msbuild'
    BuildTarget = 'Aladin.Max.sln'
    # legacy csproj (ToolsVersion 15.0 + packages.config). dotnet build로는 빌드되지 않는다.
    NeedsNuGetRestore = $true
    Note = '.NET FW 4.8 legacy. macOS에서 SAST 전무였던 C# 400파일 — Windows 전용 커버리지'
  }
  'tobe' = @{
    # 기준 브랜치 예외 (사용자 결정 2026-07-29) — 10 repo 중 유일한 예외다.
    # origin/main(2026-01-16)은 실제로 컴파일되지 않는다:
    #   Aladin.Tobe.Bll\Search\SearchEngine.cs(582,32) error CS0103 'isInternal'.
    # develop 대비 565커밋 뒤이고 develop에서는 해당 참조가 사라져 빌드 클린이다.
    # 빌드 성공이 C# 분석의 전제라 main으로는 596파일을 어떤 도구로도 분석할 수 없다.
    Path = 'tobe\Tobe'; Ref = 'origin/develop'; SonarKey = 'tobe'
    SonarMode = 'msbuild'; FortifyMode = 'msbuild'; Globs = $GlobsWebFull
    BuildTarget = 'Aladin.Tobe.sln'
    NeedsNuGetRestore = $true
    # 대상 중 최대. macOS에서 4G로는 scan이 메모리 부족으로 실패해 12G로 올렸다.
    # 12G는 macOS가 C#을 건너뛴 상태(프론트 자산만)에서 정한 값이라, C# 43,623 ncloc이
    # 더해진 Windows 실제 규모를 위해 여유를 둬 24G로 올렸다. 머신 RAM 64GB.
    #
    # 주의 — 12G가 부족하다는 것이 증명된 것은 아니다. 2026-07-29에 "12G 상한에서 정지"로
    # 판단했던 것은 오진이었다. 부모 java의 CPU만 보고 정체로 봤는데, 실제로는 자식
    # aspcodegen.exe(ASP.NET 뷰 코드 생성)가 코어 하나를 100% 쓰며 정상 진행 중이었고
    # 부모는 자식을 기다려 유휴로 보였을 뿐이다. .rsp 번역 자식의 힙 상한은 이미 약 57GB였다.
    # 진행 여부는 부모가 아니라 aspcodegen/dotnet-translator의 CPU 증가로 판단해야 한다.
    Heap = '24G'
    Note = '.NET FW 4.8 legacy + JS/CSS. C# 596파일 — Windows 전용 커버리지'
  }
}

$ServiceMap = @{
  'aasm' = @('aasm')
  'naru' = @('naru-server')
  'max'  = @('max-server','max-front','maxcms-front','maxcms-api','max-api')
  'tobe' = @('tobe')
}

# ── 인자 처리 ───────────────────────────────────────────────────────────────

if ($SaveToken) { Save-SonarToken; exit 0 }

if (-not $Target -or $Target.Count -eq 0) {
  Die "대상을 지정해라. 예: .\run-static-scan.ps1 -Target all`n     도움말: Get-Help .\run-static-scan.ps1 -Detailed"
}
if ($SonarOnly -and $FortifyOnly) { Die '-SonarOnly 와 -FortifyOnly 는 동시에 쓸 수 없다' }

$requested = New-Object System.Collections.Generic.List[string]
foreach ($t in $Target) {
  if ($t -eq 'all') {
    # 점검 대상 제외분(T-SQL 2건)은 all 에서 빠진다. 개별 키 지정으로는 실행 가능.
    $excludedFromAll = @('max-db-script','tobe-db-script')
    $Registry.Keys | Where-Object { $excludedFromAll -notcontains $_ } | ForEach-Object { $requested.Add($_) }
  } elseif ($t -like 'svc:*') {
    $svc = $t.Substring(4)
    if (-not $ServiceMap.ContainsKey($svc)) { Die "알 수 없는 서비스: $svc (aasm naru max tobe)" }
    $ServiceMap[$svc] | ForEach-Object { $requested.Add($_) }
  } elseif ($Registry.Contains($t)) {
    # repo 키가 서비스명보다 우선한다. 더 구체적인 쪽이 이겨야 한다.
    $requested.Add($t)
  } elseif ($ServiceMap.ContainsKey($t)) {
    $ServiceMap[$t] | ForEach-Object { $requested.Add($_) }
  } else {
    Die "알 수 없는 대상: $t (서비스는 svc:aasm svc:naru svc:max svc:tobe)"
  }
}
# 레지스트리 순서 유지 + 중복 제거
# 정렬은 레지스트리 전체 키 기준(제외 대상도 개별 지정 시 살아 있어야 한다).
$selected = @($Registry.Keys | Where-Object { $requested -contains $_ })

# ── 사전 점검 ───────────────────────────────────────────────────────────────

# StrictMode에서 미선언 변수를 읽으면 예외가 난다. finally의 정리 루틴이 아래 변수들을
# 읽으므로 preflight가 조기 실패해도 안전하도록 미리 선언한다.
$script:SonarToken = $null
$script:SourceAnalyzer = $null
$script:FprUtility = $null
$script:SonarScannerCli = $null
$script:SonarScannerMsBuild = $null
$script:DotnetSonarScanner = $null
$script:MsBuildExe = $null
$script:NuGetExe = $null
$SonarScannerCli = $null
$SonarScannerMsBuild = $null
$DotnetSonarScanner = $null
$MsBuildExe = $null
$NuGetExe = $null

function Find-Command {
  param([string]$Name)
  $c = Get-Command $Name -ErrorAction SilentlyContinue
  if ($c) { return $c.Source }
  return $null
}

function Find-MsBuild {
  # vswhere stderr가 'Stop'에서 사전 점검을 죽이지 않게 한다.
  $ErrorActionPreference = 'Continue'
  # vswhere가 VS Build Tools 설치 경로를 알려준다. VS 2017 이상에서 표준 경로다.
  $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
  if (Test-Path $vswhere) {
    $p = & $vswhere -latest -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\MSBuild.exe' 2>$null |
         Select-Object -First 1
    if ($p -and (Test-Path $p)) { return $p }
  }
  return (Find-Command 'msbuild.exe')
}

function Invoke-Preflight {
  $needSonar = -not $FortifyOnly
  $needFortify = -not $SonarOnly

  if (-not (Find-Command 'git.exe')) { Die 'git 없음' }

  $modes = @($selected | ForEach-Object { $Registry[$_].SonarMode })
  $needMsBuild = ($modes -contains 'msbuild')
  $needDotnet  = ($modes -contains 'dotnet')

  # Fortify의 msbuild 모드도 MSBuild.exe·nuget.exe를 쓴다. 예전에는 이 탐지가 $needSonar
  # 블록 안에만 있어서 -FortifyOnly로 돌리면 $script:MsBuildExe가 $null로 남았다.
  # 그러면 Fortify 호출이 `sourceanalyzer -b id -Xmx <빈값> <sln> /t:Rebuild ...` 가 되어
  # sourceanalyzer가 솔루션과 스위치를 전부 '번역할 파일'로 취급한다.
  # 실측 2026-07-29: FPR에 "[101] File t:Rebuild not found", 번역 0/201, MSBuild 미실행(로그 2줄).
  # 도구 탐지는 Sonar/Fortify 어느 쪽이 필요해도 수행해야 한다.
  $fortifyModes = @($selected | ForEach-Object { $Registry[$_].FortifyMode })
  $needMsBuildTool = $needMsBuild -or ($needFortify -and ($fortifyModes -contains 'msbuild'))

  if ($needSonar) {
    $script:SonarToken = Get-SonarToken

    $script:SonarScannerCli = Find-Command 'sonar-scanner.bat'
    if (-not $script:SonarScannerCli) { $script:SonarScannerCli = Find-Command 'sonar-scanner' }
    if (($modes -contains 'cli') -and -not $script:SonarScannerCli) {
      Die "sonar-scanner CLI 없음. 설치 후 PATH에 추가해라.`n     https://docs.sonarsource.com/ → SonarScanner CLI"
    }

    if ($needDotnet) {
      if (-not (Find-Command 'dotnet.exe')) { Die 'dotnet SDK 없음' }
      $script:DotnetSonarScanner = Find-Command 'dotnet-sonarscanner.exe'
      if (-not $script:DotnetSonarScanner) {
        Die "dotnet-sonarscanner 없음. 설치: dotnet tool install --global dotnet-sonarscanner"
      }
    }

    if ($needMsBuild) {
      # .NET Framework legacy는 Roslyn 기반 MSBuild 스캐너가 필수다.
      # dotnet-sonarscanner(.NET Core flavor)로는 legacy csproj를 처리하지 못한다.
      $script:SonarScannerMsBuild = Find-Command 'SonarScanner.MSBuild.exe'
      if (-not $script:SonarScannerMsBuild) {
        Die @"
SonarScanner.MSBuild.exe 없음. .NET Framework repo(max-api, tobe) 스캔에 필수다.
     sonar-scanner-msbuild-<ver>-net-framework 를 받아 PATH에 추가해라.
     dotnet-sonarscanner(.NET Core flavor)는 legacy csproj를 처리하지 못한다.
"@
      }
    }

    if (-not $DryRun) {
      $v = Invoke-SonarApi '/api/authentication/validate'
      if (-not $v -or -not $v.valid) { Die "SonarQube 토큰 무효 또는 서버 연결 실패 ($SonarHost)" }
    }
  }

  # MSBuild·nuget 탐지는 $needSonar 밖에 둔다. Fortify msbuild 모드에도 필요하므로
  # -FortifyOnly 로 돌릴 때 $null로 남으면 안 된다 (위 $needMsBuildTool 주석 참조).
  if ($needMsBuildTool) {
    $script:MsBuildExe = Find-MsBuild
    if (-not $script:MsBuildExe) {
      Die "MSBuild.exe 없음. Visual Studio Build Tools 2022 + .NET Framework 4.8 targeting pack 을 설치해라."
    }
    $script:NuGetExe = Find-Command 'nuget.exe'
    if (-not $script:NuGetExe) {
      Write-Warn 'nuget.exe 없음. MSBuild.exe는 자동 복원을 하지 않으므로 복원 실패로 빌드가 깨진다.'
    }
  }

  if ($needFortify) {
    $sa = Join-Path $FortifyHome 'bin\sourceanalyzer.exe'
    if (-not (Test-Path $sa)) { $sa = Join-Path $FortifyHome 'bin\sourceanalyzer.bat' }
    if (-not (Test-Path $sa)) {
      Die "sourceanalyzer 없음: $FortifyHome\bin`n     FORTIFY_HOME 환경변수로 설치 경로를 지정해라."
    }
    $script:SourceAnalyzer = $sa
    $fu = Join-Path $FortifyHome 'bin\FPRUtility.exe'
    if (-not (Test-Path $fu)) { $fu = Join-Path $FortifyHome 'bin\FPRUtility.bat' }
    if (-not (Test-Path $fu)) { Die "FPRUtility 없음: $FortifyHome\bin" }
    $script:FprUtility = $fu
    if (-not (Test-Path (Join-Path $FortifyHome 'fortify.license'))) {
      Write-Warn "Fortify 라이선스 파일이 $FortifyHome 에 없다"
    }
  }
}

# ── worktree 준비 ───────────────────────────────────────────────────────────
#
# 사용자 작업 트리를 건드리지 않기 위해 기준 ref를 별도 worktree로 체크아웃한다.
# macOS 실측에서 대상 repo 7/10이 feature·deploy 브랜치에 있었고 일부는 uncommitted
# 변경을 보유했다. 체크아웃 전환이나 stash는 하지 않는다.

$script:RunRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("team2-static-scan-" + [System.Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $script:RunRoot -Force | Out-Null
$script:ActiveSrc = $null
$script:ActiveWt = $null
$script:ActiveBuildId = $null

function Remove-Worktree {
  param([string]$Src, [string]$Wt)
  # PS 5.1은 네이티브 stderr를 NativeCommandError로 감싼다. 전역 'Stop'이면 git의 정상적인
  # 경고 한 줄에도 정리 루틴이 죽어 worktree가 등록된 채 남는다 (실측: 고아 worktree 3건).
  # 정리는 실패해도 계속 진행해야 하므로 함수 스코프에서 낮춘다.
  $ErrorActionPreference = 'Continue'
  if (-not $Src -or -not $Wt) { return }
  $real = try { (Resolve-Path -LiteralPath $Wt -ErrorAction Stop).Path } catch { $null }
  if (-not $real) { return }
  # 정리 대상을 이번 실행 루트 아래로 한정한다. 환경으로 주입된 경로를 지우지 않는다.
  if (-not $real.StartsWith($script:RunRoot, [StringComparison]::OrdinalIgnoreCase)) {
    Write-Warn "정리 건너뜀 (실행 루트 밖 경로): $real"
    return
  }
  & git -C $Src worktree remove --force $real 2>$null | Out-Null
  if (Test-Path $real) { Remove-Item -LiteralPath $real -Recurse -Force -ErrorAction SilentlyContinue }
  & git -C $Src worktree prune 2>$null | Out-Null
}

function Invoke-Cleanup {
  # 정리 루틴은 어떤 경우에도 중단되면 안 된다 (Remove-Worktree와 같은 이유).
  $ErrorActionPreference = 'Continue'
  if ($script:ActiveWt -and -not $KeepWorktree) {
    Remove-Worktree -Src $script:ActiveSrc -Wt $script:ActiveWt
  }
  if ($script:ActiveBuildId -and $script:SourceAnalyzer) {
    & $script:SourceAnalyzer -b $script:ActiveBuildId -clean 2>$null | Out-Null
  }
  if (-not $KeepWorktree -and (Test-Path $script:RunRoot)) {
    Remove-Item -LiteralPath $script:RunRoot -Recurse -Force -ErrorAction SilentlyContinue
  } elseif ($KeepWorktree) {
    Write-Log "임시 루트 유지: $($script:RunRoot)"
  }
}

function New-RepoWorktree {
  param([string]$Key, [string]$RelPath, [string]$Ref, [string]$RelPathAlt)
  # git 호출이 stderr를 쓰면 'Stop'에서 죽는다. 성공 판정은 $LASTEXITCODE로 한다.
  $ErrorActionPreference = 'Continue'
  $src = Join-Path $WorkspaceRoot $RelPath
  $wt = Join-Path $script:RunRoot $Key

  if (-not (Test-Path (Join-Path $src '.git')) -and $RelPathAlt) {
    $alt = Join-Path $WorkspaceRoot $RelPathAlt
    if (Test-Path (Join-Path $alt '.git')) {
      Write-Info "$Key : $RelPath 없음 -> $RelPathAlt 사용"
      $src = $alt
    }
  }
  if (-not (Test-Path (Join-Path $src '.git'))) {
    $hint = if ($RelPathAlt) { "$RelPath 또는 $RelPathAlt" } else { $RelPath }
    Write-Warn "$Key : git repo 아님 ($WorkspaceRoot\$hint)"
    return $null
  }
  & git -C $src fetch --quiet origin 2>$null | Out-Null

  $resolved = $Ref
  & git -C $src rev-parse --verify --quiet $Ref 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) {
    $alt = if ($Ref -eq 'origin/main') { 'origin/master' } elseif ($Ref -eq 'origin/master') { 'origin/main' } else { $null }
    if ($alt) {
      & git -C $src rev-parse --verify --quiet $alt 2>$null | Out-Null
      if ($LASTEXITCODE -eq 0) { Write-Warn "$Key : $Ref 없음 -> $alt 사용"; $resolved = $alt }
      else { Write-Warn "$Key : 기준 ref 없음 ($Ref)"; return $null }
    } else { Write-Warn "$Key : 기준 ref 없음 ($Ref)"; return $null }
  }

  & git -C $src worktree prune 2>$null | Out-Null
  & git -C $src worktree add --detach --quiet $wt $resolved 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Warn "$Key : worktree 생성 실패"; Remove-Worktree -Src $src -Wt $wt; return $null }

  $script:ActiveSrc = $src
  $script:ActiveWt = $wt
  return @{
    Path = $wt
    Src  = $src
    Ref  = $resolved
    Sha  = (& git -C $wt rev-parse --short HEAD).Trim()
    Date = (& git -C $wt log -1 --format=%ad --date=short).Trim()
  }
}

# ── SonarQube ───────────────────────────────────────────────────────────────

# scanner가 남기는 report-task.txt의 ceTaskId로 서버 큐 처리 완료를 기다린다.
# 이 확인 없이 measures를 읽으면 기존 프로젝트는 '이전 분석값'을 즉시 돌려준다.
# CLI는 .scannerwork\, MSBuild/.NET 스캐너는 .sonarqube\out\.sonar\ 에 남긴다.
function Wait-CeTask {
  param([string]$Src, [string]$LogFile)
  $tf = Get-ChildItem -LiteralPath $Src -Recurse -Filter 'report-task.txt' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match 'scannerwork|sonarqube' } | Select-Object -First 1
  if (-not $tf) {
    $tf = Get-ChildItem -LiteralPath $Src -Recurse -Filter 'report-task.txt' -File -ErrorAction SilentlyContinue | Select-Object -First 1
  }
  $ceId = $null
  if ($tf) {
    $line = Select-String -Path $tf.FullName -Pattern '^ceTaskId=' | Select-Object -First 1
    if ($line) { $ceId = ($line.Line -replace '^ceTaskId=', '').Trim() }
  }

  # SonarScanner for .NET 11.x는 end 단계가 성공하면 .sonarqube\out 을 정리한다.
  # 그 결과 report-task.txt 탐색이 .NET 대상에서 항상 실패해 완전 스캔이 거짓 PARTIAL로 떨어진다.
  # 실측 (maxcms-api, 2026-07-29): ANALYSIS SUCCESSFUL·CE SUCCESS·cs=10802 인데도 NO_TASK_FILE.
  # 스캐너가 로그에 남기는 CE task URL에서 id를 회수한다.
  # 로그는 Set-Content(UTF8) 헤더 뒤에 `*>>` 추가분이 붙어 인코딩이 섞일 수 있으므로 두 가지로 시도한다.
  if (-not $ceId -and (Test-Path $LogFile)) {
    $bytes = [System.IO.File]::ReadAllBytes($LogFile)
    foreach ($enc in @([System.Text.Encoding]::UTF8, [System.Text.Encoding]::Unicode)) {
      $m = [regex]::Match($enc.GetString($bytes), 'api/ce/task\?id=([0-9A-Za-z_\-]{16,})')
      if ($m.Success) { $ceId = $m.Groups[1].Value; break }
    }
  }

  if (-not $ceId) { return $(if ($tf) { 'NO_TASK_ID' } else { 'NO_TASK_FILE' }) }
  Add-Content -Path $LogFile -Value "ceTaskId=$ceId"

  $waited = 0
  $unknown = 0
  while ($waited -lt $CePollMaxSec) {
    $r = Invoke-SonarApi "/api/ce/task?id=$ceId"
    $status = if ($r -and $r.task) { $r.task.status } else { $null }
    switch ($status) {
      'SUCCESS'     { return 'SUCCESS' }
      'FAILED'      { return 'FAILED' }
      'CANCELED'    { return 'CANCELED' }
      'PENDING'     { $unknown = 0 }
      'IN_PROGRESS' { $unknown = 0 }
      default {
        # 빈 응답·일시적 오류는 재시도한다. 연속 반복 시에만 실패로 본다.
        $unknown++
        Add-Content -Path $LogFile -Value "ce poll unexpected ($unknown): $status"
        if ($unknown -ge 5) { return "UNKNOWN:$(if($status){$status}else{'empty'})" }
      }
    }
    Start-Sleep -Seconds $CePollIntervalSec
    $waited += $CePollIntervalSec
  }
  return "TIMEOUT_${CePollMaxSec}s"
}

$SonarExclusions = (@(
  '**/node_modules/**','**/.next/**','**/dist/**','**/build/**','**/bin/**','**/obj/**'
  '**/coverage/**','**/vendor/**','**/*.min.js','**/*.min.css'
) + $TestExcludes) -join ','

function Invoke-SonarScan {
  param($Key, $Cfg, $Wt, [string]$LogFile)

  # Windows PowerShell 5.1은 `*>>` 로 리다이렉트한 네이티브 명령의 stderr를
  # NativeCommandError ErrorRecord로 감싼다. 전역 $ErrorActionPreference='Stop'과 만나면
  # rc=0인데도 첫 stderr 한 줄에서 스크립트가 죽는다.
  # 실측: 스캐너의 JRE 프로비저닝 안내(정보성 stderr)에서 maxcms-api가 즉시 중단됐다.
  # 아래 네이티브 호출은 전부 $LASTEXITCODE로 성공을 판정하므로 stderr를 오류로 볼 필요가 없다.
  # 함수 스코프로만 낮춘다 (다른 구간의 cmdlet 엄격성은 유지).
  $ErrorActionPreference = 'Continue'

  if ($DryRun) { return @{ Result = 'DRY'; Note = "$($Cfg.SonarMode) -> $($Cfg.SonarKey)" } }

  $version = "$($Wt.Date)-$($Wt.Sha)"
  $rc = 0
  Push-Location $Wt.Path
  try {
    switch ($Cfg.SonarMode) {
      'cli' {
        $sonarArgs = @(
          "-Dsonar.projectKey=$($Cfg.SonarKey)"
          "-Dsonar.scm.provider=git"
          # New Code 기준이 PREVIOUS_VERSION인데 projectVersion이 분석 간 동일하면 leak period가
          # 리셋되지 않고 첫 분석 이후로 계속 누적된다 (macOS 실측: 6개월 공백 -> new_violations 37~233).
          "-Dsonar.projectVersion=$version"
        )
        if (-not (Test-Path 'sonar-project.properties')) {
          $sonarArgs += "-Dsonar.sources=."
          $sonarArgs += "-Dsonar.exclusions=$SonarExclusions"
        }
        if ($Key -like '*-db-script') {
          # T-SQL 분석기 기본 확장자는 .tsql 이라 .sql을 명시하지 않으면 아무것도 잡히지 않는다.
          # .sql 소유권이 PL/SQL 분석기와 충돌하므로 PL/SQL은 비충돌 확장자로 밀어둔다.
          $sonarArgs += "-Dsonar.tsql.file.suffixes=.sql,.tsql"
          $sonarArgs += "-Dsonar.plsql.file.suffixes=.pks,.pkb"
        }
        # SONAR_TOKEN/SONAR_HOST_URL 환경으로 넘겨 인자 노출을 없앤다.
        $env:SONAR_TOKEN = $script:SonarToken
        $env:SONAR_HOST_URL = $SonarHost
        try {
          & $script:SonarScannerCli @sonarArgs *>> $LogFile
          $rc = $LASTEXITCODE
        } finally {
          Remove-Item Env:\SONAR_TOKEN -ErrorAction SilentlyContinue
          Remove-Item Env:\SONAR_HOST_URL -ErrorAction SilentlyContinue
        }
      }
      'dotnet' {
        $target = $Cfg.BuildTarget
        if ($target -and -not (Test-Path $target)) {
          return @{ Result = 'FAIL'; Note = "빌드 대상 없음: $target" }
        }
        # SonarScanner for .NET은 SONAR_TOKEN 환경을 읽지 않는다. 인자 노출은 문서화된 잔존 위험.
        & $script:DotnetSonarScanner begin "/k:$($Cfg.SonarKey)" "/v:$version" `
            "/d:sonar.host.url=$SonarHost" "/d:sonar.token=$($script:SonarToken)" *>> $LogFile
        if ($LASTEXITCODE -eq 0) { & dotnet build $target --nologo -v minimal *>> $LogFile }
        if ($LASTEXITCODE -eq 0) { & $script:DotnetSonarScanner end "/d:sonar.token=$($script:SonarToken)" *>> $LogFile }
        $rc = $LASTEXITCODE
      }
      'msbuild' {
        $target = $Cfg.BuildTarget
        if (-not (Test-Path $target)) {
          return @{ Result = 'FAIL'; Note = "빌드 대상 없음: $target" }
        }
        # MSBuild.exe는 dotnet CLI와 달리 자동 복원을 하지 않는다. SDK-style(PackageReference)도
        # 복원 없이는 컴파일이 실패하고, 컴파일이 없으면 Roslyn 번역·분석도 없다.
        # 그래서 NeedsNuGetRestore 여부와 무관하게 msbuild 모드에서는 항상 복원한다.
        # (nuget.exe restore는 packages.config와 PackageReference를 모두 처리한다.)
        if ($script:NuGetExe) {
          & $script:NuGetExe restore $target *>> $LogFile
        }
        & $script:SonarScannerMsBuild begin "/k:$($Cfg.SonarKey)" "/v:$version" `
            "/d:sonar.host.url=$SonarHost" "/d:sonar.token=$($script:SonarToken)" *>> $LogFile
        # Configuration=Release 필수. 기본값 Debug는 Web.Debug.config를 요구하는데
        # max-api·tobe 둘 다 그 파일이 없어 TransformWebConfig 타겟에서 빌드가 깨진다 (실측 2026-07-29).
        if ($LASTEXITCODE -eq 0) { & $script:MsBuildExe $target /t:Rebuild /nologo /v:minimal /p:Configuration=Release *>> $LogFile }
        if ($LASTEXITCODE -eq 0) { & $script:SonarScannerMsBuild end "/d:sonar.token=$($script:SonarToken)" *>> $LogFile }
        $rc = $LASTEXITCODE
      }
      default { return @{ Result = 'FAIL'; Note = "알 수 없는 SonarMode: $($Cfg.SonarMode)" } }
    }
  } finally { Pop-Location }

  if ($rc -ne 0) { return @{ Result = 'FAIL'; Note = "scanner rc=$rc — 로그: $LogFile" } }

  $ce = Wait-CeTask -Src $Wt.Path -LogFile $LogFile
  if ($ce -eq 'SUCCESS') { return @{ Result = 'OK'; Note = "$($Cfg.SonarKey) (CE SUCCESS)" } }
  return @{ Result = 'PARTIAL'; Note = "$($Cfg.SonarKey) — 업로드는 됐으나 서버 처리 확인 실패 (CE=$ce). 측정값은 이전 분석일 수 있다" }
}

# ── Fortify ─────────────────────────────────────────────────────────────────

# translate가 실제로 넘기는 대상과 같은 제외 규칙을 적용해야 한다.
# 분모가 다르면 커버리지 게이트가 거짓 PARTIAL을 낸다
# (macOS 실측: tobe에서 min.js 104건이 분모에만 남아 84%로 오판됐다).
$ExpectedExcludeRe = '(^|/)(node_modules|\.next|dist|build|bin|obj|coverage|vendor)/|\.min\.(js|css)$|(^|/)docs/|\.md$|/src/test/|/src/testFixtures/|(^|/)(e2e|cypress|playwright)/|(^|/)\.devops/tests/|\.(test|spec)\.[jt]sx?$|\.test\.mjs$|(Test|Tests)\.cs$'

function Get-ExpectedFileCount {
  param($Src, $Globs, $SrcDirs)
  # git ls-files stderr가 'Stop'에서 커버리지 분모 계산을 죽이지 않게 한다.
  $ErrorActionPreference = 'Continue'
  if (-not $Globs) { return 0 }
  $total = 0
  $exts = @($Globs | ForEach-Object { ($_ -split '\.')[-1] } | Select-Object -Unique)
  foreach ($ext in $exts) {
    $patterns = if ($SrcDirs) { @($SrcDirs | ForEach-Object { "$_/*.$ext" }) } else { @("*.$ext") }
    foreach ($pat in $patterns) {
      $files = & git -C $Src ls-files $pat 2>$null
      if ($files) {
        $total += (@($files | Where-Object { $_ -notmatch $ExpectedExcludeRe })).Count
      }
    }
  }
  return $total
}

# Fortify는 내부 분석 오류가 있어도 FPR을 만들고 rc=0을 돌려준다. 로그와 FPR 오류를 직접 본다.
function Test-FortifyHealth {
  param([string]$Fpr, [string]$LogFile)
  # FPRUtility는 진단을 stderr로 쓴다. 'Stop'이면 게이트 검사 자체가 죽는다.
  $ErrorActionPreference = 'Continue'
  $errs = 0
  $out = & $script:FprUtility -information -errors -project $Fpr 2>$null
  if ($out) { $errs = (@($out | Where-Object { $_ -match 'Fatal|code \d+|Unexpected exception' })).Count }
  $logbad = 0
  if (Test-Path $LogFile) {
    $logbad = (@(Select-String -Path $LogFile -Pattern 'results may be incomplete|Unexpected exception|Fatal:' -ErrorAction SilentlyContinue)).Count
  }
  return @{ FprErrors = $errs; LogWarnings = $logbad }
}

# -analyzerIssueCounts는 analyzer 그룹 수이고 심각도가 아니다.
# 게이트 기준(Critical/High)에 맞춰 priority별로 센다.
# 파싱 실패를 0으로 떨어뜨리면 "Critical 0건"이라는 거짓 통과가 나온다.
function Get-FortifySeverity {
  param([string]$Fpr)
  # 같은 이유. 파싱 실패는 ParseOk=$false로 PARTIAL 처리하므로 예외로 죽일 필요가 없다.
  $ErrorActionPreference = 'Continue'
  $counts = [ordered]@{}
  $ok = $true
  foreach ($v in @('critical','high','medium','low')) {
    $raw = (& $script:FprUtility -information -search -project $Fpr -query "[fortify priority order]:$v" 2>$null |
            Select-Object -First 1)
    if ($raw -match '^No issues matched') { $counts[$v] = 0 }
    elseif ($raw -match '^(\d+) issues of') { $counts[$v] = [int]$Matches[1] }
    else { $counts[$v] = '?'; $ok = $false }
  }
  return @{ Counts = $counts; ParseOk = $ok }
}

function Invoke-FortifyScan {
  param($Key, $Cfg, $Wt, [string]$OutDir, [string]$LogFile)

  # Invoke-SonarScan과 같은 이유. sourceanalyzer/msbuild/nuget 는 진행 상황을 stderr로 쓴다.
  # 'Stop'이면 translate 첫 줄에서 스크립트가 죽는다. rc는 아래에서 명시적으로 판정한다.
  $ErrorActionPreference = 'Continue'

  if ($DryRun) { return @{ Result = 'DRY'; Note = "translate+scan ($($Cfg.FortifyMode)) -> $Key.fpr" } }

  $heap = if ($Cfg.ContainsKey('Heap')) { $Cfg.Heap } else { $FortifyHeapDefault }
  $buildId = "team2-$script:RunStamp-$Key-$PID"
  $fpr = Join-Path $OutDir "$Key.fpr"

  # translate 제외: 빌드 산출물·의존성 + 문서.
  # 문서를 빼는 이유는 실측 근거다. macOS에서 AASM 13 Critical 전부가 docs/*.md 의
  # 환경변수 예시와 localstack 픽스처였다. 문서 예시로 게이트가 막히면 게이트가 무의미해진다.
  $trExcl = @(
    '-exclude','**/node_modules/**','-exclude','**/.next/**','-exclude','**/dist/**'
    '-exclude','**/build/**','-exclude','**/bin/**','-exclude','**/obj/**'
    '-exclude','**/vendor/**','-exclude','**/coverage/**'
    '-exclude','**/*.min.js','-exclude','**/*.min.css'
    '-exclude','**/docs/**','-exclude','**/*.md'
  )
  # 테스트 코드 제외 (TestExcludes 와 동일 목록)
  foreach ($te in $TestExcludes) { $trExcl += @('-exclude', $te) }

  # -filter 는 scan 단계 인자다. translate에 주면 적용되지 않는다 (macOS 실측 확인).
  $scanArgs = @()
  if ($Cfg.ContainsKey('ScanFilter')) {
    $sf = Join-Path $Wt.Path $Cfg.ScanFilter
    if (Test-Path $sf) { $scanArgs += @('-filter', $sf) }
  }

  $script:ActiveBuildId = $buildId
  & $script:SourceAnalyzer -b $buildId -clean *>> $LogFile
  if ($LASTEXITCODE -ne 0) {
    return @{ Result = 'FAIL'; Note = 'build state clean 실패 — 이전 상태 혼입 위험' }
  }

  Push-Location $Wt.Path
  try {
    if ($Cfg.FortifyMode -eq 'msbuild') {
      # .NET은 빌드 통합 번역을 쓴다. 소스만 넘기면 Roslyn 의미 정보가 없어 커버리지가 떨어진다.
      $target = $Cfg.BuildTarget
      if (-not (Test-Path $target)) {
        return @{ Result = 'FAIL'; Note = "빌드 대상 없음: $target" }
      }
      # MsBuildExe가 $null이면 sourceanalyzer가 솔루션·스위치를 '번역할 파일'로 삼아
      # 조용히 번역 0건이 된다. 조용한 오판을 만들지 않도록 여기서 끊는다.
      if (-not $script:MsBuildExe) {
        return @{ Result = 'FAIL'; Note = 'MSBuild.exe 미탐지 — Fortify msbuild 번역 불가 (사전 점검 확인)' }
      }
      # Sonar 쪽과 같은 이유로 항상 복원한다. 복원 누락이 maxcms-api 번역 0/201의 원인이었다.
      # 실측 2026-07-29: 복원 후 동일 인자로 .cs 200/201 번역 성공.
      if ($script:NuGetExe) {
        & $script:NuGetExe restore $target *>> $LogFile
      }
      # Sonar 쪽과 같은 이유로 Configuration=Release를 명시한다.
      # /t:Rebuild도 필수다 — Fortify 빌드 통합 번역은 실제로 컴파일되는 파일만 잡으므로
      # 증분 빌드로는 번역 0건이 된다 (실측: dotnet build 재실행 시 files=0).
      & $script:SourceAnalyzer -b $buildId "-Xmx$heap" $script:MsBuildExe $target /t:Rebuild /nologo /p:Configuration=Release *>> $LogFile
      $rc = $LASTEXITCODE
      # 혼합 repo는 프론트 자산을 별도 translate로 덧붙인다 (tobe: js/jsx/cshtml 등).
      if ($rc -eq 0 -and $Cfg.ContainsKey('Globs') -and $Cfg.Globs) {
        $gl = if ($Cfg.ContainsKey('SrcDirs') -and $Cfg.SrcDirs) {
                @($Cfg.SrcDirs | ForEach-Object { $d = $_; $Cfg.Globs | ForEach-Object { "$d/$_" } })
              } else { $Cfg.Globs }
        & $script:SourceAnalyzer -b $buildId "-Xmx$heap" @trExcl @gl *>> $LogFile
        $rc = $LASTEXITCODE
      }
    } else {
      # 글로브는 Fortify가 직접 해석해야 한다. 셸이 먼저 확장하면 재귀 탐색이 사라진다
      # (macOS bash 실측: AASM 193 -> 70파일). PowerShell은 인자를 확장하지 않으므로
      # 문자열 그대로 전달된다.
      $gl = if ($Cfg.ContainsKey('SrcDirs') -and $Cfg.SrcDirs) {
              @($Cfg.SrcDirs | ForEach-Object { $d = $_; $Cfg.Globs | ForEach-Object { "$d/$_" } })
            } else { $Cfg.Globs }
      if (-not $gl -or $gl.Count -eq 0) {
        return @{ Result = 'FAIL'; Note = 'translate 글로브 미정의 (레지스트리 Globs 확인)' }
      }
      & $script:SourceAnalyzer -b $buildId "-Xmx$heap" @trExcl @gl *>> $LogFile
      $rc = $LASTEXITCODE
    }
  } finally { Pop-Location }

  if ($rc -ne 0) { return @{ Result = 'FAIL'; Note = "translate rc=$rc — 로그: $LogFile" } }

  $shownFiles = @(& $script:SourceAnalyzer -b $buildId -show-files 2>$null)
  # StrictMode(Latest)에서는 없는 키를 읽으면 PropertyNotFoundStrict 예외가 난다.
  # Globs 없는 repo(maxcms-api·max-api)에서 여기가 터져 이후 대상이 통째로 스캔되지 않았다.
  # 실측: max-api·tobe가 실행조차 안 됐는데 런처는 exit 0을 반환했다.
  $cfgGlobs = if ($Cfg.ContainsKey('Globs')) { $Cfg.Globs } else { $null }
  # msbuild 모드는 C#을 빌드 통합으로 번역하므로 Globs에 .cs가 없다. 그대로 두면 분모가 0이 되어
  # 커버리지 게이트가 무력화된다. .cs를 분모에 넣어 게이트가 실제로 동작하게 한다.
  # (tobe처럼 Globs로 프론트 자산을 덧붙이는 repo는 둘을 합친다.)
  $expectedGlobs = if ($Cfg.FortifyMode -eq 'msbuild') {
                     @('**/*.cs') + @(if ($cfgGlobs) { $cfgGlobs } else { @() })
                   } else { $cfgGlobs }
  $expected = Get-ExpectedFileCount -Src $Wt.Path -Globs $expectedGlobs -SrcDirs $(if ($Cfg.ContainsKey('SrcDirs')) { $Cfg.SrcDirs } else { $null })

  # 분자·분모의 단위를 맞춘다. -show-files는 분모에 없는 확장자(.csproj 등)까지 세므로
  # 그대로 비교하면 100%를 넘고 게이트가 느슨해진다.
  # 실측 2026-07-29: maxcms-api가 206/201 (102%)로 나왔다 (.cs 200 + 기타 6 / .cs 201).
  # 그 상태로는 ".cs 100 + 기타 106"도 102%로 보여 실제 누락을 가린다.
  $expectedExts = @($expectedGlobs | ForEach-Object { ($_ -split '\.')[-1].ToLower() } | Select-Object -Unique)
  $translated = if ($expectedExts.Count -gt 0) {
                  @($shownFiles | Where-Object {
                      $ext = ([System.IO.Path]::GetExtension($_) -replace '^\.','').ToLower()
                      $expectedExts -contains $ext
                    }).Count
                } else { $shownFiles.Count }
  # Globs 없는 repo(.NET msbuild 모드)는 분모가 0이 된다. 예전에는 그때 pct=100으로 떨어뜨렸는데,
  # 그러면 "한 파일도 번역되지 않은" 스캔이 커버리지 100% OK로 통과한다.
  # 실측 2026-07-29: maxcms-api가 번역 0/0 (100%)·이슈 0건으로 OK 판정됐고, FPR에는
  # "[101] File t:Rebuild not found" 번역 오류가 들어 있었다. 거짓 통과다.
  # 분모를 못 구하면 커버리지는 '미산정'($null)으로 두고, 번역 0건은 별도로 걸러낸다.
  $pct = if ($expected -gt 0) { [math]::Floor($translated * 100 / $expected) } else { $null }
  $pctStr = if ($null -eq $pct) { '미산정' } else { "$pct%" }

  & $script:SourceAnalyzer -b $buildId "-Xmx$heap" -scan @scanArgs -f $fpr *>> $LogFile
  $rc = $LASTEXITCODE
  if ($rc -ne 0 -or -not (Test-Path $fpr)) {
    $note = if (Test-Path $LogFile) {
      if (Select-String -Path $LogFile -Pattern 'not enough memory available' -Quiet) {
        "scan 메모리 부족 (-Xmx$heap) — 힙을 올리거나 머신이 한가할 때 재실행. 로그: $LogFile"
      } else { "scan rc=$rc — 로그: $LogFile" }
    } else { "scan rc=$rc" }
    return @{ Result = 'FAIL'; Note = $note }
  }

  $health = Test-FortifyHealth -Fpr $fpr -LogFile $LogFile
  $sev = Get-FortifySeverity -Fpr $fpr
  $sevStr = (($sev.Counts.Keys | ForEach-Object { "$_=$($sev.Counts[$_])" }) -join ' ')
  $note = "$sevStr | 번역 $translated/$expected ($pctStr) | fpr: $fpr"

  & $script:SourceAnalyzer -b $buildId -clean 2>$null | Out-Null
  $script:ActiveBuildId = $null

  # 한 파일도 번역되지 않았으면 스캔이 성립하지 않았다. 이슈 0건은 "깨끗함"이 아니라 "안 봤음"이다.
  # 커버리지 게이트는 분모가 0이면 이걸 못 잡으므로 별도 조건으로 둔다.
  if ($translated -eq 0) {
    return @{ Result = 'FAIL'; Note = "$note | 번역된 파일 0건 — 스캔 미성립. FPR 오류를 확인해라: $($script:FprUtility) -information -errors -project $fpr" }
  }

  if (-not $sev.ParseOk) {
    return @{ Result = 'PARTIAL'; Note = "$note | 심각도 집계 파싱 실패 — 수치 신뢰 불가" }
  }
  if ($health.FprErrors -gt 0 -or $health.LogWarnings -gt 0) {
    return @{ Result = 'PARTIAL'; Note = "$note | 분석 오류 $($health.FprErrors)건·로그 경고 $($health.LogWarnings)건 — 결과 불완전" }
  }
  # $pct가 $null이면 분모를 못 구한 것이다. PowerShell에서 $null -lt 90 은 $true가 되어
  # "커버리지 % < 90%"라는 엉뚱한 메시지가 나오므로 명시적으로 분리한다.
  if ($null -eq $pct) {
    return @{ Result = 'PARTIAL'; Note = "$note | 번역 커버리지 분모 미산정 — 완전 스캔 여부 확인 불가" }
  }
  if ($pct -lt $CoverageThresholdPct) {
    return @{ Result = 'PARTIAL'; Note = "$note | 번역 커버리지 $pct% < $CoverageThresholdPct%" }
  }
  return @{ Result = 'OK'; Note = $note }
}

# ── 실행 ────────────────────────────────────────────────────────────────────

$script:RunStamp = (Get-Date -Format 'yyyyMMdd-HHmmss')
$runDate = (Get-Date -Format 'yyyy-MM-dd')

try {
  Invoke-Preflight

  $outDir = Join-Path $OutRoot $runDate
  $logDir = Join-Path $outDir 'logs'
  New-Item -ItemType Directory -Path $logDir -Force | Out-Null
  $summary = Join-Path $outDir "summary-$($script:RunStamp).md"

  Write-Log ''
  Write-Log "정적 점검 실행 (Windows) — 대상 $($selected.Count) repo"
  Write-Log '  기준 브랜치: origin/main (없으면 origin/master)'
  Write-Log "  출력: $outDir"
  if ($DryRun) { Write-Log '  ** DRY RUN — 실제 스캔 없음 **' }
  Write-Log ''

  $rows = New-Object System.Collections.Generic.List[string]
  $details = New-Object System.Collections.Generic.List[string]
  $skips = New-Object System.Collections.Generic.List[string]
  $partials = New-Object System.Collections.Generic.List[string]
  $fails = New-Object System.Collections.Generic.List[string]

  foreach ($key in $selected) {
    $cfg = $Registry[$key]
    Write-Log "[$key] $($cfg.Path) ($($cfg.Ref))"

    $altPath = if ($cfg.Contains('PathAlt')) { $cfg.PathAlt } else { $null }
    $wt = New-RepoWorktree -Key $key -RelPath $cfg.Path -Ref $cfg.Ref -RelPathAlt $altPath
    if (-not $wt) {
      $rows.Add("| ``$key`` | $($cfg.Ref) | - | WORKTREE 실패 | WORKTREE 실패 |")
      $fails.Add("- ``$key``: worktree 준비 실패")
      $script:ActiveWt = $null; $script:ActiveSrc = $null
      continue
    }
    Write-Info "worktree: $($wt.Ref) @ $($wt.Sha) ($($wt.Date))"

    $logFile = Join-Path $logDir "$key.log"
    Set-Content -Path $logFile -Value '' -Encoding UTF8

    $sonar = @{ Result = '-'; Note = '' }
    $fortify = @{ Result = '-'; Note = '' }

    if (-not $FortifyOnly) {
      $sonar = Invoke-SonarScan -Key $key -Cfg $cfg -Wt $wt -LogFile $logFile
      Write-Info "SonarQube: $($sonar.Result)$(if($sonar.Note){" — $($sonar.Note)"})"
    }
    if (-not $SonarOnly) {
      $fortify = Invoke-FortifyScan -Key $key -Cfg $cfg -Wt $wt -OutDir $outDir -LogFile $logFile
      Write-Info "Fortify:   $($fortify.Result)$(if($fortify.Note){" — $($fortify.Note)"})"
    }

    $rows.Add("| ``$key`` | $($wt.Ref -replace '^origin/','') | ``$($wt.Sha)`` ($($wt.Date)) | $($sonar.Result) | $($fortify.Result) |")
    $details.Add("### ``$key``")
    $details.Add('')
    $details.Add("- 경로: ``$($cfg.Path)`` @ ``$($wt.Ref)`` (``$($wt.Sha)``, $($wt.Date))")
    $details.Add("- 비고: $($cfg.Note)")
    $details.Add("- SonarQube: **$($sonar.Result)**$(if($sonar.Note){" — $($sonar.Note)"})")
    $details.Add("- Fortify: **$($fortify.Result)**$(if($fortify.Note){" — $($fortify.Note)"})")
    $details.Add('')

    foreach ($pair in @(@('SonarQube', $sonar), @('Fortify', $fortify))) {
      switch ($pair[1].Result) {
        'SKIP'    { $skips.Add("- ``$key`` $($pair[0]): $($pair[1].Note)") }
        'PARTIAL' { $partials.Add("- ``$key`` $($pair[0]): $($pair[1].Note)") }
        'FAIL'    { $fails.Add("- ``$key`` $($pair[0]): $($pair[1].Note)") }
      }
    }

    Remove-Worktree -Src $wt.Src -Wt $wt.Path
    $script:ActiveWt = $null; $script:ActiveSrc = $null
  }

  $sb = New-Object System.Collections.Generic.List[string]
  $sb.Add("# 정적 점검 결과 (Windows) — $runDate")
  $sb.Add('')
  $sb.Add("- 실행: ``$($script:RunStamp)``")
  $sb.Add('- 티켓: DEV2-7594')
  $sb.Add('- 기준 브랜치: ``origin/main`` 우선, 없으면 ``origin/master``')
  $sb.Add("- SonarQube: $SonarHost")
  $sb.Add("- 대상 repo: $($selected.Count)개")
  $sb.Add('- 플랫폼: Windows — macOS에서 SKIP되던 .NET C#(`max-api`·`tobe`·`maxcms-api`)이 포함된다')
  if ($DryRun) { $sb.Add('- **DRY RUN — 실제 스캔 미수행**') }
  $sb.Add('')
  $sb.Add('## 요약')
  $sb.Add('')
  $sb.Add('| repo | 기준 | commit | SonarQube | Fortify |')
  $sb.Add('|---|---|---|---|---|')
  $rows | ForEach-Object { $sb.Add($_) }

  if ($fails.Count -gt 0) {
    $sb.Add(''); $sb.Add('## 실패'); $sb.Add('')
    $fails | ForEach-Object { $sb.Add($_) }
  }
  if ($partials.Count -gt 0) {
    $sb.Add(''); $sb.Add('## 부분 결과 (PARTIAL — 수치를 신뢰하지 말 것)'); $sb.Add('')
    $partials | ForEach-Object { $sb.Add($_) }
    $sb.Add('')
    $sb.Add('Fortify는 내부 분석 오류가 있어도 FPR을 만들고 rc=0을 반환한다.')
    $sb.Add('PARTIAL은 FPR 오류·로그 경고 또는 번역 커버리지 미달을 뜻하므로 완전 스캔으로 취급하면 안 된다.')
  }
  if ($skips.Count -gt 0) {
    $sb.Add(''); $sb.Add('## 커버리지 공백 (SKIP)'); $sb.Add('')
    $skips | ForEach-Object { $sb.Add($_) }
  }
  $sb.Add(''); $sb.Add('## 상세'); $sb.Add('')
  $details | ForEach-Object { $sb.Add($_) }

  Set-Content -Path $summary -Value ($sb -join "`r`n") -Encoding UTF8

  Write-Log ''
  Write-Log "완료. 요약: $summary"

  if ($fails.Count -gt 0) { Write-Log '실패 있음 -> exit 1'; exit 1 }
  if ($FailOnSkip -and $skips.Count -gt 0) { Write-Log '커버리지 공백 있음 (-FailOnSkip) -> exit 1'; exit 1 }
  if ($skips.Count -gt 0 -or $partials.Count -gt 0) { Write-Log '공백/부분 결과 있음 -> exit 2'; exit 2 }
  exit 0
}
finally {
  Invoke-Cleanup
}
