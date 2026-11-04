# 只保存本机后端连接配置，不连接数据库，也不执行SQL。
param (
    [string]$DbHost = 'localhost',
    [int]$DbPort = 3306
)

$ErrorActionPreference = 'Stop'
$configPath = Join-Path $PSScriptRoot '.local-db.json'
$securePassword = Read-Host 'Password for approval_app (Enter = ApprovalDb2026!)' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)

try {
    $appPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)

    if ([string]::IsNullOrEmpty($appPassword)) {
        $appPassword = 'ApprovalDb2026!'
    }

    @{
        host     = $DbHost
        port     = $DbPort
        username = 'approval_app'
        password = $appPassword
    } |
        ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8

    Write-Host 'Local configuration saved. This script did not execute any SQL.' -ForegroundColor Green
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $securePassword.Dispose()
}
