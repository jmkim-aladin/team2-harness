[CmdletBinding()]
param(
    [string]$HarnessPath,
    [string]$WorkspacePath,
    [switch]$CloneRepos
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $HarnessPath) {
    $HarnessPath = (Resolve-Path (Join-Path $ScriptDir "..")).Path
}
else {
    $HarnessPath = (Resolve-Path -LiteralPath $HarnessPath).Path
}

if (-not $WorkspacePath) {
    $WorkspacePath = Split-Path -Parent $HarnessPath
}
else {
    $WorkspacePath = (Resolve-Path -LiteralPath $WorkspacePath).Path
}

$ClaudeDir = Join-Path $HOME ".claude"
$ClaudeCommandsDir = Join-Path $ClaudeDir "commands"
$ClaudeAdPath = Join-Path $ClaudeCommandsDir "ad"
$HarnessAdPath = Join-Path $HarnessPath ".claude\commands\ad"
$SettingsPath = Join-Path $ClaudeDir "settings.json"

New-Item -ItemType Directory -Force -Path $ClaudeDir, $ClaudeCommandsDir | Out-Null

[Environment]::SetEnvironmentVariable("TEAM2_HARNESS_PATH", $HarnessPath, "User")
[Environment]::SetEnvironmentVariable("TEAM2_WORKSPACE_PATH", $WorkspacePath, "User")
[Environment]::SetEnvironmentVariable("YOUTRACK_BASE_URL", "https://aladincommunication.youtrack.cloud", "User")
$env:TEAM2_HARNESS_PATH = $HarnessPath
$env:TEAM2_WORKSPACE_PATH = $WorkspacePath
$env:YOUTRACK_BASE_URL = "https://aladincommunication.youtrack.cloud"

if (Test-Path -LiteralPath $SettingsPath) {
    $settings = Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
}
else {
    $settings = [pscustomobject]@{}
}

if (-not $settings.PSObject.Properties["env"]) {
    $settings | Add-Member -NotePropertyName "env" -NotePropertyValue ([pscustomobject]@{})
}

$settings.env | Add-Member -Force -NotePropertyName "TEAM2_HARNESS_PATH" -NotePropertyValue $HarnessPath
$settings.env | Add-Member -Force -NotePropertyName "TEAM2_WORKSPACE_PATH" -NotePropertyValue $WorkspacePath
$settings.env | Add-Member -Force -NotePropertyName "YOUTRACK_BASE_URL" -NotePropertyValue "https://aladincommunication.youtrack.cloud"
$settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $SettingsPath -Encoding UTF8

if (Test-Path -LiteralPath $ClaudeAdPath) {
    $existing = Get-Item -LiteralPath $ClaudeAdPath
    $sameTarget = $false

    if ($existing.LinkType -and $existing.Target) {
        $sameTarget = ($existing.Target -contains $HarnessAdPath)
    }

    if (-not $sameTarget) {
        $backupPath = "$ClaudeAdPath.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
        Move-Item -LiteralPath $ClaudeAdPath -Destination $backupPath
        Write-Host "Backed up existing Claude ad commands to $backupPath"
    }
}

if (-not (Test-Path -LiteralPath $ClaudeAdPath)) {
    try {
        New-Item -ItemType Junction -Path $ClaudeAdPath -Target $HarnessAdPath | Out-Null
    }
    catch {
        New-Item -ItemType SymbolicLink -Path $ClaudeAdPath -Target $HarnessAdPath | Out-Null
    }
}

if ($CloneRepos) {
    & (Join-Path $ScriptDir "clone-catalog-repos.ps1") -WorkspacePath $WorkspacePath
}

Write-Host "TEAM2_HARNESS_PATH=$HarnessPath"
Write-Host "TEAM2_WORKSPACE_PATH=$WorkspacePath"
Write-Host "Claude commands: $ClaudeAdPath -> $HarnessAdPath"

if (Get-Command gh -ErrorAction SilentlyContinue) {
    gh --version | Select-Object -First 1
    gh auth status
    if ($LASTEXITCODE -ne 0) {
        Write-Host "gh authentication is required: gh auth login"
    }
}
else {
    Write-Host "gh CLI is not installed. Install from https://cli.github.com/ and run gh auth login."
}

exit 0
