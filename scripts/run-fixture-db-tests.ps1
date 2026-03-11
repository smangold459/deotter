param(
    [switch]$KeepRunning
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $repoRoot "test-fixtures\databases\docker-compose.yml"
$javaOutDir = Join-Path $HOME ".deotter\bin"
$jdbcDriversDir = Join-Path $HOME ".deotter\drivers"

function Get-PythonCommand {
    $venvPython = Join-Path $repoRoot "python\.venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return @($venvPython)
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return @("py", "-3")
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return @("python")
    }

    throw "Could not find a Python runtime. Install Python or create python/.venv."
}

function Invoke-Python {
    param(
        [string[]]$Args
    )

    $cmd = Get-PythonCommand
    if ($cmd.Length -gt 1) {
        & $cmd[0] $cmd[1..($cmd.Length - 1)] @Args
    }
    else {
        & $cmd[0] @Args
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Args -join ' ')"
    }
}

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Wait-ForHealthyContainer {
    param(
        [string]$ContainerName,
        [int]$MaxAttempts = 60,
        [int]$SleepSeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $status = docker inspect -f "{{.State.Health.Status}}" $ContainerName 2>$null
        if ($LASTEXITCODE -eq 0 -and $status -eq "healthy") {
            Write-Host "$ContainerName is healthy."
            return
        }

        if ($attempt -eq $MaxAttempts) {
            throw "Timed out waiting for $ContainerName to become healthy."
        }

        Start-Sleep -Seconds $SleepSeconds
    }
}

function Build-TempConfig {
    param(
        [string]$TempHomePath,
        [bool]$IncludeSybase
    )

    $configDir = Join-Path $TempHomePath ".config\deotter"
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null

    $aliases = @("sqlite", "postgres", "mysql", "mssql")
    if ($IncludeSybase) {
        $aliases += "sybase"
    }

    $sqliteDbPath = (Join-Path $repoRoot "test-fixtures\databases\sqlite\database.sqlite") -replace "\\", "/"

    $configLines = @(
        "databases=$($aliases -join ',')",
        "",
        "sqlite.url=jdbc:sqlite:$sqliteDbPath",
        "sqlite.user=",
        "sqlite.password=",
        "",
        "postgres.url=jdbc:postgresql://localhost:5432/deotter",
        "postgres.user=deotter",
        "postgres.password=deotter",
        "",
        "mysql.url=jdbc:mysql://localhost:3306/deotter?allowPublicKeyRetrieval=true&useSSL=false",
        "mysql.user=deotter",
        "mysql.password=deotter",
        "",
        "mssql.url=jdbc:sqlserver://localhost:1433;databaseName=deotter;encrypt=false;trustServerCertificate=true",
        "mssql.user=sa",
        "mssql.password=StrongPassw0rd!"
    )

    if ($IncludeSybase) {
        $configLines += @(
            "",
            "sybase.url=$env:DEOTTER_SYBASE_JDBC_URL",
            "sybase.user=$env:DEOTTER_SYBASE_USER",
            "sybase.password=$env:DEOTTER_SYBASE_PASSWORD"
        )
    }

    $configFile = Join-Path $configDir "config.properties"
    $configLines | Set-Content -Path $configFile -Encoding Ascii
    return $configFile
}

Require-Command -Name docker
Require-Command -Name javac

Write-Host "Generating fixture SQL and SQLite database..."
Invoke-Python -Args @("scripts/generate-iris-fixtures.py")

Write-Host "Compiling Java sources..."
& (Join-Path $repoRoot "scripts\compile-java.ps1") -OutDir $javaOutDir -MainOnly
if ($LASTEXITCODE -ne 0) {
    throw "Java compilation failed."
}

Write-Host "Starting fixture database containers..."
docker compose -f $composeFile up -d postgres mysql mssql
if ($LASTEXITCODE -ne 0) {
    throw "Failed to start fixture containers."
}

$stopContainers = -not $KeepRunning

try {
    Wait-ForHealthyContainer -ContainerName "deotter-postgres-fixture"
    Wait-ForHealthyContainer -ContainerName "deotter-mysql-fixture"
    Wait-ForHealthyContainer -ContainerName "deotter-mssql-fixture"

    Write-Host "Seeding MSSQL fixture schema from init.sql..."
    docker exec deotter-mssql-fixture /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "StrongPassw0rd!" -No -Q "IF DB_ID('deotter') IS NULL CREATE DATABASE deotter"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create deotter database in MSSQL container."
    }

    docker exec deotter-mssql-fixture /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "StrongPassw0rd!" -No -d deotter -i /fixtures/mssql/init.sql
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to load MSSQL fixture SQL."
    }

    $includeSybase = [bool]$env:DEOTTER_SYBASE_JDBC_URL
    if ($includeSybase -and (-not $env:DEOTTER_SYBASE_USER)) {
        throw "DEOTTER_SYBASE_USER is required when DEOTTER_SYBASE_JDBC_URL is set."
    }
    if ($includeSybase -and (-not $env:DEOTTER_SYBASE_PASSWORD)) {
        throw "DEOTTER_SYBASE_PASSWORD is required when DEOTTER_SYBASE_JDBC_URL is set."
    }

    $tempHome = Join-Path ([System.IO.Path]::GetTempPath()) ("deotter-fixture-home-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tempHome -Force | Out-Null

    try {
        $configPath = Build-TempConfig -TempHomePath $tempHome -IncludeSybase $includeSybase
        Write-Host "Using temporary config file: $configPath"

        $jarPaths = @()
        if (Test-Path $jdbcDriversDir) {
            $jarPaths = Get-ChildItem -Path $jdbcDriversDir -Filter *.jar -File | ForEach-Object { $_.FullName }
        }
        $cpParts = @($javaOutDir) + $jarPaths
        $classpath = [string]::Join([IO.Path]::PathSeparator, $cpParts)

        Write-Host "Running Java fixture validation test..."
        & java "-Duser.home=$tempHome" -cp $classpath com.deotter.tests.TestConn
        if ($LASTEXITCODE -ne 0) {
            throw "Fixture validation failed. See output above."
        }

        Write-Host "Fixture validation completed successfully."
    }
    finally {
        if (Test-Path $tempHome) {
            Remove-Item -Path $tempHome -Recurse -Force
        }
    }
}
finally {
    if ($stopContainers) {
        Write-Host "Stopping fixture containers..."
        docker compose -f $composeFile down -v
    }
}
