param(
    [string]$OutDir,
    [switch]$MainOnly,
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $OutDir) {
    $OutDir = Join-Path $repoRoot "python\resources\out"
}

$javac = Get-Command javac -ErrorAction SilentlyContinue
if (-not $javac) {
    throw "Could not find 'javac' on PATH. Install a JDK and ensure javac is available."
}

$mainSources = Get-ChildItem (Join-Path $repoRoot "java\main\*.java") -File -ErrorAction SilentlyContinue
$testSources = @()
if (-not $MainOnly) {
    $testSources = Get-ChildItem (Join-Path $repoRoot "java\tests\*.java") -File -ErrorAction SilentlyContinue
}

$sources = @($mainSources + $testSources)
if ($sources.Count -eq 0) {
    throw "No Java source files were found under java/main or java/tests."
}

if ($Clean -and (Test-Path $OutDir)) {
    Remove-Item $OutDir -Recurse -Force
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

$sourcePaths = $sources | ForEach-Object { $_.FullName }
Write-Host "Compiling $($sourcePaths.Count) Java file(s) to $OutDir"
& $javac.Source -d $OutDir @sourcePaths
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "Java compilation complete."
