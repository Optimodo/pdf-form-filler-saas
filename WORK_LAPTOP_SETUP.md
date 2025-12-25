# Work Laptop Development Setup - Easy Cleanup Guide

## Reality Check: What Can vs Can't Be in One Directory

### ✅ Can Be in One Directory (Portable/Easy to Remove)
- **Project folder** - All your code
- **Docker volumes/data** - Can be exported/moved
- **Database backups** - SQL dumps

### ❌ Must Be System-Installed (Can't Avoid)
- **Docker Desktop** - System application (Windows/Mac installer)
- **Git** - System application (though can use portable version)
- **Node.js/npm** - Usually system-installed (or use nvm in user directory)
- **Python** - Usually system-installed (or use portable)
- **Cursor/IDE** - Usually system-installed

## Recommended Organization Strategy

### Option 1: Single Development Directory (Recommended) ⭐

Create one main directory for all development work:

```
C:\Users\mikem\Development\          (or wherever you prefer)
├── projects\
│   └── pdf-form-filler-saas\        ← Your project
├── backups\
│   └── database-backup.sql          ← Database exports
└── notes\
    └── setup-notes.txt              ← Installation notes
```

**Benefits:**
- ✅ Easy to find everything
- ✅ Easy to backup entire folder
- ✅ Easy to delete when leaving

**Limitations:**
- ❌ Docker Desktop still needs system install
- ❌ But Docker data can be exported

### Option 2: Portable Tools Where Possible

Some tools have portable versions you can put in your directory:

```
C:\Users\mikem\Development\
├── tools\
│   ├── GitPortable\                 ← Portable Git (optional)
│   ├── nvm\                         ← Node Version Manager (user directory)
│   └── Python\                      ← Portable Python (optional)
├── projects\
│   └── pdf-form-filler-saas\
└── backups\
```

## Practical Setup for Your Project

### What You Actually Need to Install:

1. **Docker Desktop** (system install - can't avoid)
   - Download from docker.com
   - Standard Windows installer
   - Stores data in `C:\ProgramData\docker` (system location)

2. **Git** (system install OR portable)
   - Option A: Standard installer (recommended for ease)
   - Option B: Portable Git in your development folder

3. **Cursor/VS Code** (system install)
   - Standard installer
   - User-specific settings (won't affect others)

4. **Node.js** (if not using Docker for frontend dev)
   - Usually system install
   - OR use nvm (Node Version Manager) - installs in user directory

### Recommended Directory Structure:

```
C:\Users\mikem\Development\          ← Your main dev folder
│
├── projects\
│   └── pdf-form-filler-saas\        ← Your project (clone here)
│       ├── backend\
│       ├── frontend\
│       ├── docker-compose.yml
│       └── .env                      ← Keep secure, don't commit
│
├── backups\
│   ├── database-backup.sql
│   └── docker-images.tar            ← If you export images
│
└── README-DEVELOPMENT.txt           ← Notes on what's installed
```

## What Gets Installed Where

### System Locations (Can't Avoid):

| Tool | Install Location | Data Location | Cleanup Method |
|------|-----------------|---------------|----------------|
| **Docker Desktop** | `C:\Program Files\Docker\` | `C:\ProgramData\docker\` | Uninstaller in Settings |
| **Git** | `C:\Program Files\Git\` | User config: `C:\Users\mikem\.gitconfig` | Uninstaller in Settings |
| **Cursor** | `C:\Users\mikem\AppData\Local\Programs\Cursor\` | Settings: `C:\Users\mikem\.cursor\` | Uninstaller in Settings |
| **Node.js** (if installed) | `C:\Program Files\nodejs\` | Cache: `C:\Users\mikem\AppData\Roaming\npm\` | Uninstaller in Settings |

### Your Development Directory:

| Item | Location | Cleanup Method |
|------|----------|----------------|
| **Project code** | `Development\projects\pdf-form-filler-saas\` | Delete folder |
| **Database backups** | `Development\backups\` | Delete folder |
| **Docker volumes** (if exported) | `Development\backups\docker-volumes\` | Delete folder |

## Easy Cleanup Strategy

### Create a Cleanup Checklist File

Create `Development\CLEANUP-CHECKLIST.txt`:

```text
CLEANUP CHECKLIST - PDF Form Filler Development

BEFORE REMOVING:
1. Export database backup (if needed)
   docker-compose exec db pg_dump -U postgres pdf_form_filler > backups/final-backup.sql

2. Export Docker images (if needed)
   docker save postgres:15 redis:7-alpine -o backups/images.tar

TO REMOVE:

1. Uninstall Docker Desktop:
   - Settings → Apps → Docker Desktop → Uninstall
   - Or: Control Panel → Programs → Docker Desktop

2. Uninstall Git (if installed):
   - Settings → Apps → Git → Uninstall

3. Uninstall Cursor:
   - Settings → Apps → Cursor → Uninstall

4. Delete development folder:
   - Delete: C:\Users\mikem\Development\
   - (Includes all projects, backups, notes)

5. Delete Docker data (if uninstaller doesn't):
   - Delete: C:\ProgramData\docker\
   - Delete: C:\Users\mikem\.docker\

6. Delete Git config (if needed):
   - Delete: C:\Users\mikem\.gitconfig

7. Delete Cursor settings (if needed):
   - Delete: C:\Users\mikem\.cursor\

8. Delete Node.js (if installed separately):
   - Settings → Apps → Node.js → Uninstall
   - Delete: C:\Users\mikem\AppData\Roaming\npm\

VERIFICATION:
- Check Settings → Apps for any remaining dev tools
- Check C:\Program Files\ for Docker, Git, Node.js
- Check user folder for .gitconfig, .docker, .cursor folders
```

## Recommended Setup Steps

### 1. Create Development Directory

```powershell
# Create main development folder
mkdir C:\Users\mikem\Development
mkdir C:\Users\mikem\Development\projects
mkdir C:\Users\mikem\Development\backups
```

### 2. Check Your Laptop Architecture

Before installing Docker Desktop, check if your laptop uses ARM64 or AMD64 (x86_64):

**Method 1: System Information (Recommended)**
```powershell
systeminfo | Select-String "System Type"
```
- `x64-based PC` = AMD64/x86_64 (most common)
- `ARM64-based PC` = ARM64 (newer Surface/Windows on ARM devices)

**Method 2: Environment Variable**
```powershell
$env:PROCESSOR_ARCHITECTURE
```
- `AMD64` = AMD64/x86_64
- `ARM64` = ARM64

**Method 3: Settings App**
- Settings → System → About
- Look at "Processor" or "System type"
- "64-bit operating system, x64-based processor" = AMD64
- "64-bit operating system, ARM-based processor" = ARM64

**Method 4: PowerShell Command**
```powershell
(Get-CimInstance Win32_Processor).Architecture
```
- `9` = x64 (AMD64)
- `12` = ARM64

### 3. Install Docker Desktop

- **For AMD64**: Download "Docker Desktop for Windows" (standard version)
- **For ARM64**: Download "Docker Desktop for Windows (ARM64)" (if available)
- Download from docker.com (choose correct architecture)
- Install normally (system install - can't avoid)
- Verify: `docker --version`

### 4. Install Git

- Download from git-scm.com
- Install normally
- OR use portable version in `Development\tools\GitPortable\`

### 5. Clone/Copy Project

```powershell
cd C:\Users\mikem\Development\projects
git clone <your-repo-url> pdf-form-filler-saas
# OR copy project folder here
```

### 6. Create Setup Notes

Create `Development\README-DEVELOPMENT.txt`:

```text
PDF Form Filler Development Environment

INSTALLED SOFTWARE:
- Docker Desktop (system install)
- Git (system install)
- Cursor IDE (system install)

PROJECT LOCATION:
C:\Users\mikem\Development\projects\pdf-form-filler-saas\

QUICK START:
cd C:\Users\mikem\Development\projects\pdf-form-filler-saas
docker-compose pull
docker-compose build
docker-compose up

BACKUP LOCATION:
C:\Users\mikem\Development\backups\

FOR CLEANUP:
See CLEANUP-CHECKLIST.txt in this folder
```

## Docker Data Management

### Export Docker Data Before Cleanup:

```powershell
# Export database
cd C:\Users\mikem\Development\projects\pdf-form-filler-saas
docker-compose exec db pg_dump -U postgres pdf_form_filler > ..\..\backups\database-backup.sql

# Export images (optional)
docker save postgres:15 redis:7-alpine dpage/pgadmin4:latest -o ..\..\backups\docker-images.tar

# List volumes (to see what exists)
docker volume ls
```

### Clean Docker Data:

```powershell
# Stop all containers
docker-compose down

# Remove volumes (WARNING: Deletes all data!)
docker-compose down -v

# Remove images
docker rmi pdf-form-filler-saas-backend pdf-form-filler-saas-frontend
docker rmi postgres:15 redis:7-alpine dpage/pgadmin4:latest

# Clean everything (WARNING: Removes ALL Docker data)
docker system prune -a --volumes
```

## Best Practices for Work Laptops

### 1. Keep Everything Documented

- Maintain `README-DEVELOPMENT.txt` with what's installed
- Keep `CLEANUP-CHECKLIST.txt` updated
- Document any custom configurations

### 2. Use Environment Variables

Keep sensitive data in `.env` files (not committed to git):
- Database passwords
- API keys
- Secret keys

### 3. Regular Backups

Export important data regularly:
- Database backups
- Configuration files
- Any custom settings

### 4. Isolate Project Data

Keep all project-related files in your `Development` folder:
- Project code ✅
- Database backups ✅
- Notes/documentation ✅
- Exported Docker volumes ✅

### 5. Use Docker for Everything Possible

- ✅ Database runs in Docker (not system install)
- ✅ Backend runs in Docker (Python not needed system-wide)
- ✅ Frontend dev server runs in Docker (Node.js not needed system-wide)
- ❌ Docker Desktop itself must be system-installed

## Minimal System Install Approach

If you want to minimize system installations:

**Must Install:**
1. Docker Desktop (system install - required)

**Can Skip (if using Docker):**
- ❌ Python (runs in Docker)
- ❌ Node.js (runs in Docker)
- ✅ Git (needed for version control, but portable version exists)

**Optional:**
- Cursor/IDE (for coding)
- Git GUI (if you prefer)

## Quick Cleanup Script (PowerShell)

Create `Development\cleanup.ps1`:

```powershell
# Cleanup script for PDF Form Filler development environment
# Run as Administrator for full cleanup

Write-Host "PDF Form Filler Development Cleanup" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow
Write-Host ""

# Stop Docker containers
Write-Host "Stopping Docker containers..." -ForegroundColor Cyan
cd "$env:USERPROFILE\Development\projects\pdf-form-filler-saas"
docker-compose down -v

# Remove Docker images
Write-Host "Removing Docker images..." -ForegroundColor Cyan
docker rmi pdf-form-filler-saas-backend pdf-form-filler-saas-frontend
docker rmi postgres:15 redis:7-alpine dpage/pgadmin4:latest

# Clean Docker system
Write-Host "Cleaning Docker system..." -ForegroundColor Cyan
docker system prune -a --volumes -f

Write-Host ""
Write-Host "Docker cleanup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Uninstall Docker Desktop from Settings → Apps"
Write-Host "2. Delete Development folder: $env:USERPROFILE\Development"
Write-Host "3. Delete Docker data: C:\ProgramData\docker (requires admin)"
Write-Host "4. Delete user Docker folder: $env:USERPROFILE\.docker"
```

## Summary

### Recommended Approach:

1. **Create single `Development` folder** for all your dev work
2. **Install Docker Desktop** (system install - can't avoid)
3. **Install Git** (system install - small footprint)
4. **Use Docker for everything else** (Python, Node.js run in containers)
5. **Keep project, backups, and notes** in `Development` folder
6. **Document cleanup process** in `CLEANUP-CHECKLIST.txt`

### What You Can Delete Easily:

✅ **Entire `Development` folder** - All your code, backups, notes
✅ **Docker volumes** - Using `docker-compose down -v`
✅ **Docker images** - Using `docker rmi` or `docker system prune`

### What Requires System Uninstall:

❌ **Docker Desktop** - Use Settings → Apps → Uninstall
❌ **Git** - Use Settings → Apps → Uninstall
❌ **Cursor/IDE** - Use Settings → Apps → Uninstall

### Bottom Line:

**You can't install everything in one directory**, but you CAN:
- ✅ Keep all project code/data in one `Development` folder
- ✅ Use Docker to avoid installing Python/Node.js system-wide
- ✅ Document everything for easy cleanup
- ✅ Use standard uninstallers for system software (takes 2 minutes)

The `Development` folder approach gives you 90% of what you want - easy organization and easy cleanup of project-specific stuff. System installs are minimal and standard uninstallers handle them cleanly.
