[CmdletBinding()]
param(
    [string]$Source = "",
    [string]$SkillSource = "",
    [string]$SourceProfile = "default",
    [string]$Profile = "openconcierge",
    [ValidateSet("interactive", "dedicated", "existing")]
    [string]$Mode = "interactive",
    [ValidateSet("desktop", "telegram")]
    [string]$Channel = "desktop",
    [switch]$Repair,
    [switch]$Yes,
    [switch]$NoDesktop
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Profile)) {
    Stop-Setup "Profile name cannot be empty." 3
}
if ([string]::IsNullOrWhiteSpace($SourceProfile)) {
    Stop-Setup "Source profile cannot be empty." 3
}

$HermesBin = if ($env:HERMES_BIN) { $env:HERMES_BIN } else { "hermes" }

function Stop-Setup {
    param(
        [string]$Message,
        [int]$Code = 3
    )
    [Console]::Error.WriteLine($Message)
    exit $Code
}

function Install-OfficialHermes {
    $temporary = Join-Path $env:TEMP ("hermes-install-{0}.ps1" -f ([guid]::NewGuid()))
    try {
        Invoke-WebRequest -Uri "https://hermes-agent.nousresearch.com/install.ps1" -OutFile $temporary
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $temporary
        if ($LASTEXITCODE -ne 0) {
            Stop-Setup "The official Hermes installer did not complete." 3
        }
    }
    catch {
        Stop-Setup "Could not download or run the official Hermes installer." 3
    }
    finally {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-Hermes {
    param(
        [Parameter(ValueFromRemainingArguments=$true)]
        [string[]]$Arguments
    )
    & $HermesBin @Arguments
}

function Test-HermesAvailable {
    if ($HermesBin -match '[\\/]') {
        return (Test-Path -LiteralPath $HermesBin)
    }
    $found = Get-Command -Name $HermesBin -ErrorAction SilentlyContinue
    return [bool]$found
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) {
    $ScriptDir = (Get-Location).Path
}
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..")).Path

function Resolve-ManifestValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ManifestPath,
        [Parameter(Mandatory = $true)]
        [string]$Key
    )
    $manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $value = $manifest.$Key
    if (-not $value) { return $null }
    $resolved = [string]$value
    if ($resolved -match '^(https?)://') {
        return $resolved
    }
    if ([System.IO.Path]::IsPathRooted($resolved)) {
        return $resolved
    }
    $manifestDir = Split-Path -Parent -Path $ManifestPath
    $manifestDir = [System.IO.Path]::GetFullPath($manifestDir)
    return [System.IO.Path]::GetFullPath((Join-Path $manifestDir $resolved))
}

function Resolve-LocalDistribution {
    if ($Source) { return }
    $manifestPath = Join-Path $ScriptDir "release.json"
    if (Test-Path -LiteralPath $manifestPath) {
        try {
            $resolved = Resolve-ManifestValue -ManifestPath $manifestPath -Key 'distribution_source'
            if ($resolved) {
                $Script:Source = $resolved
                return
            }
        }
        catch {
            $manifest = $null
        }
    }
    $candidate = Join-Path $RepoRoot "distribution.yaml"
    if (Test-Path -LiteralPath $candidate) {
        $Script:Source = $RepoRoot
    }
}

function Resolve-SkillSource {
    if ($SkillSource) { return }
    $manifestPath = Join-Path $ScriptDir "release.json"
    if (Test-Path -LiteralPath $manifestPath) {
        try {
            $resolved = Resolve-ManifestValue -ManifestPath $manifestPath -Key 'skill_source'
            if ($resolved) {
                $Script:SkillSource = $resolved
            }
        }
        catch {
            return
        }
    }
}

Resolve-LocalDistribution
Resolve-SkillSource

function Get-AbsolutePath {
    param([string]$PathValue)
    if ([string]::IsNullOrEmpty($PathValue)) { return $PathValue }
    if ([System.IO.Path]::IsPathRooted($PathValue)) { return $PathValue }
    $combined = Join-Path (Get-Location) $PathValue
    return [System.IO.Path]::GetFullPath($combined)
}

switch ($Mode) {
    "dedicated" {
        if (-not $Source) {
            Stop-Setup "No distribution source found. Pass -Source PATH to a directory containing distribution.yaml." 3
        }
        $Source = Get-AbsolutePath $Source
        if (-not (Test-Path -LiteralPath (Join-Path $Source "distribution.yaml"))) {
            Stop-Setup "Distribution source $Source is missing distribution.yaml." 3
        }
        if (-not (Test-Path -LiteralPath (Join-Path $Source "skills\openconcierge\SKILL.md"))) {
            Stop-Setup "Distribution source $Source is missing skills\openconcierge\SKILL.md." 3
        }
    }
    "existing" {
        if (-not $SkillSource) {
            Stop-Setup "No skill source found. Pass -SkillSource URL or a published skill identifier." 3
        }
    }
    "interactive" {
        if ($Yes -and -not [Console]::IsInputRedirected) {
            Stop-Setup "Interactive mode requires a terminal. Pass -Mode dedicated or -Mode existing with -Yes." 3
        }
        Write-Host "Choose an installation mode:"
        Write-Host "  1. Dedicated OpenConcierge profile"
        Write-Host "  2. Add the OpenConcierge skill to an existing profile"
        Write-Host "Enter 1 or 2: "
        if ([Console]::IsInputRedirected) {
            $selection = "1"
        }
        else {
            $selection = Read-Host
        }
        switch ($selection.Trim()) {
            "1" { $Mode = "dedicated" }
            "2" { $Mode = "existing" }
            default { Stop-Setup "Installation cancelled." 2 }
        }
    }
}

if (-not (Test-HermesAvailable)) {
    if (-not $Yes) {
        if ([Console]::IsInputRedirected) {
            Stop-Setup "Hermes is not on PATH. Run with -Yes to allow the installer to fetch the official Hermes installer, or install Hermes first." 3
        }
        Write-Host "OpenConcierge needs Hermes to continue. Install Hermes now? [y/N]"
        $confirm = Read-Host
        if ($confirm -notmatch '^[yY]([eE][sS])?$') {
            Stop-Setup "Cancelled. Install Hermes from https://hermes-agent.nousresearch.com and re-run this installer." 2
        }
    }
    Install-OfficialHermes
    if (-not (Test-HermesAvailable)) {
        Stop-Setup "Hermes did not become available after the official installer ran." 3
    }
}

$doctorResult = & $HermesBin doctor
$doctorExit = $LASTEXITCODE
if ($doctorExit -ne 0) {
    Stop-Setup "Hermes is installed but the local environment is unhealthy. Run 'hermes doctor' for details." 3
}

$SearchKeywords = @(
    "web",
    "search",
    "mcp",
    "exa",
    "tavily",
    "brave",
    "duckduckgo",
    "serp",
    "firecrawl",
    "searx",
    "parallel",
    "xai"
)

function Test-SearchCapability {
    param([string]$ToolsOutput)
    if ([string]::IsNullOrEmpty($ToolsOutput)) { return $false }
    $lower = $ToolsOutput.ToLower()
    foreach ($keyword in $SearchKeywords) {
        if ($lower -match [regex]::Escape($keyword)) { return $true }
    }
    return $false
}

switch ($Mode) {
    "dedicated" {
        $profileCreateOutput = & $HermesBin profile create $Profile --clone-from $SourceProfile
        $createExit = $LASTEXITCODE
        if ($createExit -eq 0) {
            & $HermesBin profile install $Source --name $Profile --alias --force --yes
            if ($LASTEXITCODE -ne 0) {
                Stop-Setup "Hermes rejected the distribution install for profile '$Profile'." 3
            }
        }
        else {
            if ($Repair -and $Yes) {
                & $HermesBin profile update $Profile --yes
                if ($LASTEXITCODE -ne 0) {
                    Stop-Setup "Hermes rejected the profile update for '$Profile'." 3
                }
            }
            else {
                Stop-Setup "Profile '$Profile' already exists. Re-run with -Repair -Yes to refresh it, or pick a different -Profile name." 2
            }
        }

        $showOutput = & $HermesBin profile show $Profile
        if ($LASTEXITCODE -ne 0) {
            Stop-Setup "Hermes did not register the expected profile. Re-run with -Repair -Yes to refresh an existing OpenConcierge profile." 4
        }
        $skillsOutput = & $HermesBin -p $Profile skills list --source all --enabled-only
        if ($LASTEXITCODE -ne 0 -or (-not ($skillsOutput -match 'openconcierge'))) {
            Stop-Setup "Hermes did not register the expected profile or skill. Re-run with -Repair -Yes to refresh an existing OpenConcierge profile." 4
        }
    }
    "existing" {
        $showOutput = & $HermesBin profile show $Profile
        if ($LASTEXITCODE -ne 0) {
            Stop-Setup "Hermes could not find profile '$Profile'." 3
        }
        & $HermesBin -p $Profile skills install $SkillSource --name openconcierge --yes
        if ($LASTEXITCODE -ne 0) {
            Stop-Setup "Hermes rejected the skill install for profile '$Profile'." 3
        }
        $skillsOutput = & $HermesBin -p $Profile skills list --source all --enabled-only
        if ($LASTEXITCODE -ne 0 -or (-not ($skillsOutput -match 'openconcierge'))) {
            Stop-Setup "Hermes did not register the expected skill. Re-run with -Repair -Yes to refresh an existing OpenConcierge skill." 4
        }
    }
}

if ($Channel -eq "telegram") {
    Write-Host "Telegram setup for the new OpenConcierge profile:"
    Write-Host "  1. Open Hermes Desktop and sign in to the new profile."
    Write-Host "  2. Go to Gateway -> Telegram in Hermes Desktop."
    Write-Host "  3. Create a new bot token for this profile. Do not reuse an active token from another profile."
    Write-Host "The installer does not start a gateway; Hermes handles that step."
    exit 0
}

$toolsOutput = & $HermesBin tools list --platform cli
if ($LASTEXITCODE -ne 0) { $toolsOutput = "" }
$hasSearch = Test-SearchCapability -ToolsOutput $toolsOutput
if (-not $hasSearch) {
    [Console]::Error.WriteLine("No compatible web search tool was detected for this profile. Open Hermes Desktop and configure a search integration (Tools, Skills, or MCP) before asking OpenConcierge to research products.")
}

if (-not $NoDesktop) {
    $desktopOutput = & $HermesBin -p $Profile desktop
    if ($LASTEXITCODE -ne 0) {
        Stop-Setup "Could not launch Hermes Desktop for profile '$Profile'. Run 'hermes -p $Profile desktop' manually." 3
    }
}

exit 0
