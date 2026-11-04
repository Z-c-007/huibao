param (
    [string]$Maven = 'D:\develop\apache-maven-3.10.0-bin\apache-maven-3.10.0\bin\mvn.cmd',
    [string]$JavaHome = 'D:\develop\Java'
)

$ErrorActionPreference = 'Stop'
$configPath = Join-Path $PSScriptRoot '.local-db.json'

if (-not (Test-Path -LiteralPath $configPath)) {
    & (Join-Path $PSScriptRoot 'configure-local.ps1')
}

if (-not (Test-Path -LiteralPath $Maven)) {
    throw 'Maven not found. Pass -Maven with the full path to mvn.cmd.'
}

if (-not (Test-Path -LiteralPath (Join-Path $JavaHome 'bin\java.exe'))) {
    throw 'JDK not found. Pass -JavaHome with the JDK 17 directory.'
}

$localConfig = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$previous = @{
    JAVA_HOME       = $env:JAVA_HOME
    APP_DB_HOST     = $env:APP_DB_HOST
    APP_DB_PORT     = $env:APP_DB_PORT
    APP_DB_PASSWORD = $env:APP_DB_PASSWORD
}

try {
    $env:JAVA_HOME = $JavaHome
    $env:APP_DB_HOST = $localConfig.host
    $env:APP_DB_PORT = [string]$localConfig.port
    $env:APP_DB_PASSWORD = $localConfig.password
    Push-Location (Join-Path $PSScriptRoot 'backend')

    try {
        & $Maven spring-boot:run

        if ($LASTEXITCODE -ne 0) {
            throw 'Backend stopped with an error. Read the Maven/application log above.'
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    $env:JAVA_HOME = $previous.JAVA_HOME
    $env:APP_DB_HOST = $previous.APP_DB_HOST
    $env:APP_DB_PORT = $previous.APP_DB_PORT
    $env:APP_DB_PASSWORD = $previous.APP_DB_PASSWORD
}
