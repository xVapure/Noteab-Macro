[CmdletBinding()]
param(
    [string]$PublicRepo = (Join-Path ([Environment]::GetFolderPath("UserProfile")) "Downloads\Coteab"),
    [string]$PublicRemote = "https://github.com/mattstellar/Coteab.git",
    [string]$ExePath = "",
    [string]$CommitMessage = "Update compiled Coteab executable",
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)][string]$Repo,
        [Parameter(Mandatory = $true)][string[]]$Args
    )

    & git -C $Repo @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed in $Repo"
    }
}

function Resolve-ExePath {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRepo,
        [string]$RequestedPath
    )

    if (-not [string]::IsNullOrWhiteSpace($RequestedPath)) {
        return (Resolve-Path -LiteralPath $RequestedPath).Path
    }

    $homeDir = [Environment]::GetFolderPath("UserProfile")
    $candidates = @(
        (Join-Path $SourceRepo "dist\CoteabMacro.exe"),
        (Join-Path $SourceRepo "dist_onefile\CoteabMacro.exe"),
        (Join-Path $SourceRepo "CoteabMacro.exe"),
        (Join-Path $homeDir "Downloads\CoteabShenanigans\CoteabMacro.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Could not find CoteabMacro.exe. Pass -ExePath with the compiled exe path."
}

function Clear-PublicRepo {
    param([Parameter(Mandatory = $true)][string]$Repo)

    $repoPath = (Resolve-Path -LiteralPath $Repo).Path
    Get-ChildItem -LiteralPath $repoPath -Force |
        Where-Object { $_.Name -ne ".git" } |
        ForEach-Object {
            if (-not $_.FullName.StartsWith($repoPath, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "Refusing to remove path outside public repo: $($_.FullName)"
            }
            Remove-Item -LiteralPath $_.FullName -Recurse -Force
        }
}

$sourceRepo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path -LiteralPath (Join-Path $sourceRepo ".git"))) {
    throw "Source repo was not found at $sourceRepo"
}

if (-not (Test-Path -LiteralPath $PublicRepo)) {
    & git clone $PublicRemote $PublicRepo
    if ($LASTEXITCODE -ne 0) {
        throw "Could not clone $PublicRemote into $PublicRepo"
    }
}

$publicRepoPath = (Resolve-Path -LiteralPath $PublicRepo).Path
if (-not (Test-Path -LiteralPath (Join-Path $publicRepoPath ".git"))) {
    throw "Public repo path is not a git repo: $publicRepoPath"
}

$originUrl = (& git -C $publicRepoPath remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not read public repo origin remote."
}
if ($originUrl -notmatch "mattstellar[/:]Coteab(\.git)?$") {
    throw "Public repo origin is '$originUrl', expected mattstellar/Coteab."
}

$resolvedExe = Resolve-ExePath -SourceRepo $sourceRepo -RequestedPath $ExePath

Clear-PublicRepo -Repo $publicRepoPath
Copy-Item -LiteralPath $resolvedExe -Destination (Join-Path $publicRepoPath "CoteabMacro.exe") -Force

$publicStatus = & git -C $publicRepoPath status --porcelain
if ($LASTEXITCODE -ne 0) {
    throw "Could not read public repo status."
}

if (-not $publicStatus) {
    Write-Host "No public executable changes to publish."
    return
}

Invoke-Git -Repo $publicRepoPath -Args @("add", "-A")
Invoke-Git -Repo $publicRepoPath -Args @("commit", "-m", $CommitMessage)

if (-not $NoPush) {
    Invoke-Git -Repo $publicRepoPath -Args @("push", "origin", "main")
}

Write-Host "Published executable-only public repo."
Write-Host "Executable: $resolvedExe"
