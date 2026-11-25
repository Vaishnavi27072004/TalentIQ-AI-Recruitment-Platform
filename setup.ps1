$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Setting up TalentFlow..." -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example."
}

Set-Location "backend"
if (-not (Test-Path "venv")) {
    py -3.10 -m venv venv
}
& ".\venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\venv\Scripts\python.exe" seed_demo_users.py

Set-Location "..\frontend"
npm install

Set-Location ".."
Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Run .\start.ps1, then open http://localhost:5173"
Write-Host "Admin login: admin@demo.com / Admin@12345"
