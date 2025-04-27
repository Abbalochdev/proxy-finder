# PowerShell cleanup script
$filesToDelete = @(
    "Filtering_Proxy_n.py",
    "Loging_Proxy.py",
    "Proxy_Fetching.py",
    "Testing_Proxy.py",
    "config.py",
    "proxy_cli.py",
    "proxy_manager.py",
    "proxy_rotation.log",
    "proxy_validator.py",
    "cleanup.bat",
    "cleanup.ps1"
)

foreach ($file in $filesToDelete) {
    if (Test-Path $file) {
        Remove-Item $file -Force
        Write-Host "Deleted $file"
    }
}

if (Test-Path "__pycache__") {
    Remove-Item "__pycache__" -Recurse -Force
    Write-Host "Deleted __pycache__ directory"
}

Write-Host "Cleanup complete!"
