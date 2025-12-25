# Quick script to restart both frontend and backend containers
Write-Host "🔄 Restarting backend and frontend..." -ForegroundColor Yellow
docker-compose restart backend frontend
Write-Host "✅ Backend and frontend restarted!" -ForegroundColor Green





