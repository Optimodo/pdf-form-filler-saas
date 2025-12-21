# Quick Restart Commands

After making code changes, you may need to restart containers for changes to take effect.

## Quick Commands

### Restart Backend Only
```powershell
docker-compose restart backend
```

### Restart Frontend Only
```powershell
docker-compose restart frontend
```

### Restart Both
```powershell
docker-compose restart backend frontend
```

## Using the Scripts

I've created PowerShell scripts you can run:

- `restart-backend.ps1` - Restarts only the backend
- `restart-frontend.ps1` - Restarts only the frontend  
- `restart-all.ps1` - Restarts both backend and frontend

To run them, right-click and "Run with PowerShell" or run:
```powershell
.\restart-backend.ps1
.\restart-frontend.ps1
.\restart-all.ps1
```

## Notes

- **Backend**: With `--reload` flag, Python code changes are auto-detected, but restarting ensures everything is fresh
- **Frontend**: React hot-reloads most changes, but sometimes a restart is needed for new files or major changes
- **No need to restart**: Database, Redis, and pgAdmin typically don't need restarts for code changes

## When to Restart

**Restart Backend if:**
- You added new Python files or modules
- You changed dependencies in `requirements.txt`
- You modified environment variables
- API endpoints aren't working as expected

**Restart Frontend if:**
- You added new React components
- You modified `package.json` dependencies
- Routing changes aren't working
- Hot reload isn't picking up changes

**Restart Both if:**
- You're not sure which one needs it
- After pulling major updates
- When things seem "stuck"


