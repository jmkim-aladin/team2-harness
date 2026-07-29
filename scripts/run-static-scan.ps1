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

# ── 설정 ────────────────────────────────────────────────────────────────────

$SonarHost = 'https://sonarqube.sec.aladin.co.kr'
$TokenFile = Join-Path $env:LOCALAPPDATA 'team2\sonarqube-token.dpapi'
$FortifyHome = if ($env:FORTIFY_HOME) { $env:FORTIFY_HOME } else { 'C:\Program Files\Fortify\Fortify_SCA_26.2.0' }
$FortifyHeapDefault = if ($env:FORTIFY_HEAP) { $env:FORTIFY_HEAP } else { '4G' }

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
    Path = 'AASM'; Ref = 'origin/main'; SonarKey = 'aasm'
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
    Path = 'max\max-api'; Ref = 'origin/main'; SonarKey = 'max-api'
    SonarMode = 'msbuild'; FortifyMode = 'msbuild'
    BuildTarget = 'Aladin.Max.sln'
    # legacy csproj (ToolsVersion 15.0 + packages.config). dotnet build로는 빌드되지 않는다.
    NeedsNuGetRestore = $true
    Note = '.NET FW 4.8 legacy. macOS에서 SAST 전무였던 C# 400파일 — Windows 전용 커버리지'
  }
  'tobe' = @{
    Path = 'tobe\Tobe'; Ref = 'origin/main'; SonarKey = 'tobe'
    SonarMode = 'msbuild'; FortifyMode = 'msbuild'; Globs = $GlobsWebFull
    BuildTarget = 'Aladin.Tobe.sln'
    NeedsNuGetRestore = $true
    # 212k ncloc으로 대상 중 최대. macOS에서 4G로는 scan이 메모리 부족으로 실패했다.
    Heap = '12G'
    Note = '.NET FW 4.8 legacy + JS/CSS. C# 596파일 — Windows 전용 커버리지'
  }
}

$ServiceMap = @{
  'aasm' = @('aasm')
  'naru' = @('naru-server')
  'max'  = @('max-server','max-front','maxcms-front','maxcms-api','max-db-script','max-api')
  'tobe' = @('tobe-db-script','tobe')
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
    $Registry.Keys | ForEach-Object { $requested.Add($_) }
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
      $script:MsBuildExe = Find-MsBuild
      if (-not $script:MsBuildExe) {
        Die "MSBuild.exe 없음. Visual Studio Build Tools 2022 + .NET Framework 4.8 targeting pack 을 설치해라."
      }
      $script:NuGetExe = Find-Command 'nuget.exe'
      if (-not $script:NuGetExe) {
        Write-Warn 'nuget.exe 없음. packages.config 기반 repo는 복원 실패로 빌드가 깨질 수 있다.'
      }
    }

    if (-not $DryRun) {
      $v = Invoke-SonarApi '/api/authentication/validate'
      if (-not $v -or -not $v.valid) { Die "SonarQube 토큰 무효 또는 서버 연결 실패 ($SonarHost)" }
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
  param([string]$Key, [string]$RelPath, [string]$Ref)
  $src = Join-Path $WorkspaceRoot $RelPath
  $wt = Join-Path $script:RunRoot $Key

  if (-not (Test-Path (Join-Path $src '.git'))) { Write-Warn "$Key : git repo 아님 ($src)"; return $null }
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
  if (-not $tf) { return 'NO_TASK_FILE' }

  $line = Select-String -Path $tf.FullName -Pattern '^ceTaskId=' | Select-Object -First 1
  if (-not $line) { return 'NO_TASK_ID' }
  $ceId = ($line.Line -replace '^ceTaskId=', '').Trim()
  if (-not $ceId) { return 'NO_TASK_ID' }
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

$SonarExclusions = '**/node_modules/**,**/.next/**,**/dist/**,**/build/**,**/bin/**,**/obj/**,**/coverage/**,**/vendor/**,**/*.min.js,**/*.min.css'

function Invoke-SonarScan {
  param($Key, $Cfg, $Wt, [string]$LogFile)

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
        if ($Cfg.ContainsKey('NeedsNuGetRestore') -and $Cfg.NeedsNuGetRestore -and $script:NuGetExe) {
          # legacy packages.config는 dotnet restore로 복원되지 않는다.
          & $script:NuGetExe restore $target *>> $LogFile
        }
        & $script:SonarScannerMsBuild begin "/k:$($Cfg.SonarKey)" "/v:$version" `
            "/d:sonar.host.url=$SonarHost" "/d:sonar.token=$($script:SonarToken)" *>> $LogFile
        if ($LASTEXITCODE -eq 0) { & $script:MsBuildExe $target /t:Rebuild /nologo /v:minimal *>> $LogFile }
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
$ExpectedExcludeRe = '(^|/)(node_modules|\.next|dist|build|bin|obj|coverage|vendor)/|\.min\.(js|css)$|(^|/)docs/|\.md$'

function Get-ExpectedFileCount {
  param($Src, $Globs, $SrcDirs)
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
      if ($Cfg.ContainsKey('NeedsNuGetRestore') -and $Cfg.NeedsNuGetRestore -and $script:NuGetExe) {
        & $script:NuGetExe restore $target *>> $LogFile
      }
      & $script:SourceAnalyzer -b $buildId "-Xmx$heap" $script:MsBuildExe $target /t:Rebuild /nologo *>> $LogFile
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

  $translated = (@(& $script:SourceAnalyzer -b $buildId -show-files 2>$null)).Count
  $expected = Get-ExpectedFileCount -Src $Wt.Path -Globs $Cfg.Globs -SrcDirs $(if ($Cfg.ContainsKey('SrcDirs')) { $Cfg.SrcDirs } else { $null })
  $pct = if ($expected -gt 0) { [math]::Floor($translated * 100 / $expected) } else { 100 }

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
  $note = "$sevStr | 번역 $translated/$expected ($pct%) | fpr: $fpr"

  & $script:SourceAnalyzer -b $buildId -clean 2>$null | Out-Null
  $script:ActiveBuildId = $null

  if (-not $sev.ParseOk) {
    return @{ Result = 'PARTIAL'; Note = "$note | 심각도 집계 파싱 실패 — 수치 신뢰 불가" }
  }
  if ($health.FprErrors -gt 0 -or $health.LogWarnings -gt 0) {
    return @{ Result = 'PARTIAL'; Note = "$note | 분석 오류 $($health.FprErrors)건·로그 경고 $($health.LogWarnings)건 — 결과 불완전" }
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

    $wt = New-RepoWorktree -Key $key -RelPath $cfg.Path -Ref $cfg.Ref
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
