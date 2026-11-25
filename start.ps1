$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Starting TalentFlow..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; .\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host "Backend: http://localhost:8000/docs"
Write-Host "Frontend: http://localhost:5173"
