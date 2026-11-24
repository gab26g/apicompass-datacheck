param([switch]$ValidateOnly, [switch]$RebuildDataCheck)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
# Windows DPAPI keeps bootstrap keys encrypted at rest, stable between launches.
# This cache is local to this Windows user; production uses AWS secret storage.
$cacheDirectory = Join-Path $PSScriptRoot '.local'
$cacheFile = Join-Path $cacheDirectory 'bootstrap.clixml'
New-Item -ItemType Directory -Force -Path $cacheDirectory | Out-Null
if (-not (Test-Path -LiteralPath $cacheFile)) {
    $bootstrap = @{}
    foreach ($name in @('JWT_SECRET', 'JWT_REFRESH_SECRET', 'CREDS_KEY', 'CREDS_IV')) {
        $byteCount = if ($name -eq 'CREDS_IV') { 16 } else { 32 }
        $plain = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes($byteCount)).ToLowerInvariant()
        $bootstrap[$name] = ConvertTo-SecureString -String $plain -AsPlainText -Force
    }
    $bootstrap | Export-Clixml -LiteralPath $cacheFile
}
$bootstrap = Import-Clixml -LiteralPath $cacheFile
try {
    foreach ($name in $bootstrap.Keys) {
        $plain = [Net.NetworkCredential]::new('', $bootstrap[$name]).Password
        [Environment]::SetEnvironmentVariable($name, $plain, 'Process')
    }
    if ($ValidateOnly) {
        & docker compose -f compose.local.yaml config --services
    } else {
        $brandOutput = Join-Path $cacheDirectory 'branding'
        New-Item -ItemType Directory -Force -Path $brandOutput | Out-Null
        $chatImages = @(& docker compose -f compose.local.yaml config --images | Where-Object { $_ -like 'ghcr.io/librechat-ai/librechat@*' })
        if ($LASTEXITCODE -ne 0 -or $chatImages.Count -ne 1) { throw 'Cannot resolve the pinned chat image.' }
        & docker run --rm --platform linux/amd64 --entrypoint node --mount "type=bind,source=$PSScriptRoot/scripts,target=/brand-scripts,readonly" --mount "type=bind,source=$brandOutput,target=/brand-output" $chatImages[0] /brand-scripts/prepare-brand.cjs
        if ($LASTEXITCODE -ne 0) { throw 'Static branding preparation failed.' }
        if ($RebuildDataCheck) {
            & docker compose -f compose.local.yaml build datacheck
            if ($LASTEXITCODE -ne 0) { throw 'DataCheck build failed.' }
        }
        & docker compose -f compose.local.yaml up -d
    }
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose failed; inspect its output above.' }
} finally {
    foreach ($name in $bootstrap.Keys) {
        [Environment]::SetEnvironmentVariable($name, $null, 'Process')
    }
    $plain = $null
}
