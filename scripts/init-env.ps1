$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) { Write-Host ".env already exists - not overwriting it."; exit 1 }
function New-Secret([int]$n) {
  $b = New-Object byte[] $n
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  -join ($b | ForEach-Object { $_.ToString("x2") })
}
$admin = New-Secret 16; $owner = New-Secret 16; $user = New-Secret 16; $key = New-Secret 32
@"
APP_ENV=development
POSTGRES_ADMIN_PASSWORD=$admin
APP_OWNER_PASSWORD=$owner
APP_USER_PASSWORD=$user
DATABASE_URL=postgresql://app_user:$user@localhost:5432/restops
MIGRATION_DATABASE_URL=postgresql://app_owner:$owner@localhost:5432/restops
TEST_DATABASE_URL=postgresql://app_owner:$owner@localhost:5432/restops_test
APP_SECRET_KEY=$key
COOKIE_SECURE=false
"@ | Set-Content -Path $envFile -Encoding ascii
Write-Host "Created .env with random local passwords. Never commit it."
