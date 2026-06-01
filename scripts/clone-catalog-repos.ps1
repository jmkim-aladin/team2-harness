[CmdletBinding()]
param(
    [string]$WorkspacePath,
    [string]$CatalogPath
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HarnessRoot = (Resolve-Path (Join-Path $ScriptDir "..")).Path

if (-not $WorkspacePath) {
    $WorkspacePath = Split-Path -Parent $HarnessRoot
}

if (-not $CatalogPath) {
    $CatalogPath = Join-Path $HarnessRoot "catalog"
}

$WorkspacePath = (Resolve-Path -LiteralPath $WorkspacePath).Path
$CatalogPath = (Resolve-Path -LiteralPath $CatalogPath).Path
$IsWindowsPlatform = ($PSVersionTable.PSEdition -eq "Desktop") -or ($IsWindows -eq $true)

function Invoke-Git {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Set-RepoGitOptions {
    param([string]$RepoPath)

    Push-Location $RepoPath
    try {
        Invoke-Git config core.longpaths true

        if ($IsWindowsPlatform) {
            # Required when the history contains paths that Git for Windows protects by default.
            Invoke-Git config core.protectNTFS false
            Invoke-Git config core.protectHFS false
        }
    }
    finally {
        Pop-Location
    }
}

function Assert-PathUnderWorkspace {
    param([string]$Path)

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $workspaceRoot = $WorkspacePath.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

    if (-not ($fullPath + [System.IO.Path]::DirectorySeparatorChar).StartsWith($workspaceRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to move or clone outside workspace: $fullPath"
    }
}

function Move-FlatRepoToTarget {
    param(
        [string]$FlatPath,
        [string]$TargetPath
    )

    Assert-PathUnderWorkspace -Path $FlatPath
    Assert-PathUnderWorkspace -Path $TargetPath

    $targetParent = Split-Path -Parent $TargetPath
    $flatFullPath = [System.IO.Path]::GetFullPath($FlatPath)
    $parentFullPath = [System.IO.Path]::GetFullPath($targetParent)

    if ($flatFullPath.Equals($parentFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        $tempPath = Join-Path $WorkspacePath ".repo-move-$([System.Guid]::NewGuid().ToString('N'))"
        Assert-PathUnderWorkspace -Path $tempPath

        Move-Item -LiteralPath $FlatPath -Destination $tempPath
        New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
        Move-Item -LiteralPath $tempPath -Destination $TargetPath
        return
    }

    New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
    Move-Item -LiteralPath $FlatPath -Destination $TargetPath
}

$windowsSparseExcludes = @{
    "Ebook_Web_Viewer" = @("!logs\\*")
    "EbookIos" = @(
        "!EpubEngineWork/Hancom/HanComEpubViewer/Resource/JS/AladinEpubView_20_0_1133_744_1133_597_XPScreenMode(rawValue: 2)__277001017_A1D5CA64-8CA2-4E3F-9833-494225E436B0_nil_000000_false.html"
    )
}

$workspaceRelativePaths = @{
    "AASM" = "s3manager"
    "BazaarServer" = "bazaar/BazaarServer"
    "Ebook_Web_Viewer" = "ebook/Ebook_Web_Viewer"
    "EbookIos" = "ebook/EbookIos"
    "EbookViewerAPI" = "ebook/EbookViewerAPI"
    "max-api" = "max/max-api"
    "max-front" = "max/max-front"
    "maxcms-api" = "max/maxcms-api"
    "maxcms-front" = "max/maxcms-front"
    "max-db-script" = "max/max-db-script"
    "max-search" = "max/max-search"
    "MaxServer" = "max/MaxServer"
    "NaruServer" = "naru/NaruServer"
    "ShoppingAndroid" = "shopping/ShoppingAndroid"
    "Tobe" = "tobe/Tobe"
    "ToBeAndroid" = "tobe/ToBeAndroid"
    "ToBeIos" = "tobe/ToBeIos"
    "tobe-db-script" = "tobe/tobe-db-script"
    "dev1-web-aladin" = "shopping/dev1-web-aladin"
    "mall-search" = "shopping/mall-search"
}

$wikiReferencedUrls = @(
    "https://github.com/AladinCommunication/dev1-web-aladin",
    "https://github.com/AladinCommunication/mall-search"
)

$urlPattern = "https://github\.com/AladinCommunication/[A-Za-z0-9_.-]+"
$urls = Get-ChildItem -LiteralPath $CatalogPath -Filter "*.yaml" -File |
    Select-String -Pattern $urlPattern -AllMatches |
    ForEach-Object { $_.Matches.Value } |
    Sort-Object -Unique

$urls = @($urls) + $wikiReferencedUrls | Sort-Object -Unique

if (-not $urls) {
    throw "No GitHub repository URLs found in $CatalogPath"
}

$results = foreach ($url in $urls) {
    $repoName = ($url.TrimEnd("/") -split "/")[-1]
    $relativePath = if ($workspaceRelativePaths.ContainsKey($repoName)) {
        $workspaceRelativePaths[$repoName]
    }
    else {
        $repoName
    }

    $targetPath = Join-Path $WorkspacePath $relativePath
    $flatPath = Join-Path $WorkspacePath $repoName
    $hasWindowsSparseRule = $IsWindowsPlatform -and $windowsSparseExcludes.ContainsKey($repoName)

    if (-not (Test-Path -LiteralPath $targetPath) -and
        $flatPath -ne $targetPath -and
        (Test-Path -LiteralPath (Join-Path $flatPath ".git"))) {
        Move-FlatRepoToTarget -FlatPath $flatPath -TargetPath $targetPath
    }

    if (Test-Path -LiteralPath $targetPath) {
        if (Test-Path -LiteralPath (Join-Path $targetPath ".git")) {
            Set-RepoGitOptions -RepoPath $targetPath

            if ($hasWindowsSparseRule) {
                Push-Location $targetPath
                try {
                    Invoke-Git sparse-checkout init --no-cone
                    $patterns = @("/*") + $windowsSparseExcludes[$repoName]
                    Invoke-Git sparse-checkout set --no-cone @patterns
                    Invoke-Git checkout -f
                }
                finally {
                    Pop-Location
                }
            }

            [pscustomobject]@{
                Repo = $repoName
                Status = "existing"
                Path = $targetPath
            }
            continue
        }

        [pscustomobject]@{
            Repo = $repoName
            Status = "skipped: path exists but is not a git repository"
            Path = $targetPath
        }
        continue
    }

    if ($hasWindowsSparseRule) {
        Assert-PathUnderWorkspace -Path $targetPath
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetPath) | Out-Null
        Invoke-Git clone --no-checkout $url $targetPath
        Set-RepoGitOptions -RepoPath $targetPath

        Push-Location $targetPath
        try {
            Invoke-Git sparse-checkout init --no-cone
            $patterns = @("/*") + $windowsSparseExcludes[$repoName]
            Invoke-Git sparse-checkout set --no-cone @patterns
            Invoke-Git checkout
        }
        finally {
            Pop-Location
        }
    }
    else {
        Assert-PathUnderWorkspace -Path $targetPath
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetPath) | Out-Null
        Invoke-Git clone $url $targetPath
        Set-RepoGitOptions -RepoPath $targetPath
    }

    [pscustomobject]@{
        Repo = $repoName
        Status = "cloned"
        Path = $targetPath
    }
}

$results | Sort-Object Repo | Format-Table -AutoSize
