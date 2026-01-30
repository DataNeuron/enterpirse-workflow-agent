# Load environment variables from .env file
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Host "Loaded: $name" -ForegroundColor Green
        }
    }
    Write-Host "✅ Environment variables loaded from .env" -ForegroundColor Green
} else {
    Write-Host "❌ .env file not found" -ForegroundColor Red
}
