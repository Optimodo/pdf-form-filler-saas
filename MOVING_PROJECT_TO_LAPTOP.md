# Moving Project to Laptop - Docker Images Guide

## Important: Docker Images Are NOT in Your Project Folder

Docker images are stored in Docker's internal storage (usually `C:\ProgramData\docker` on Windows or `~/.docker` on Mac/Linux), **not** in your project folder.

Just copying the project folder will **NOT** transfer Docker images.

## Option 1: Pull Images on New Laptop (Requires Internet) ⭐ Recommended

This is the easiest method if you'll have internet when setting up.

### Steps:

1. **Copy project folder** to laptop (via USB drive, cloud sync, git clone, etc.)

2. **Install Docker Desktop** on the laptop (if not already installed)

3. **Open terminal in project folder** and run:
   ```bash
   docker-compose pull
   ```
   This downloads all images defined in your `docker-compose.yml`

4. **Or build locally** (if you've customized Dockerfiles):
   ```bash
   docker-compose build
   ```

5. **Start containers**:
   ```bash
   docker-compose up
   ```

### What Gets Copied vs Pulled:

**Copied with Project Folder:**
- ✅ Source code
- ✅ `docker-compose.yml`
- ✅ `Dockerfile`s
- ✅ Configuration files
- ✅ `.env` files (if included)

**Must Be Pulled/Built (NOT in project folder):**
- ❌ Docker images (PostgreSQL, Redis, your app images)
- ❌ Docker volumes (database data, storage files)

## Option 2: Export/Import Images (No Internet Needed)

If you won't have internet when setting up, you can export images from your current machine and import on the laptop.

### On Current Machine (Before Travel):

1. **Save all images to a file**:
   ```bash
   # Save all images used by docker-compose
   docker save $(docker-compose config --images) -o docker-images.tar
   
   # Or save individual images
   docker save postgres:15 redis:7-alpine -o docker-images.tar
   ```

2. **Copy the `.tar` file** to laptop (via USB, cloud, etc.)
   - Note: This file can be 2-5 GB in size!

### On New Laptop:

1. **Load the images**:
   ```bash
   docker load -i docker-images.tar
   ```

2. **Start containers**:
   ```bash
   docker-compose up
   ```

### Pros/Cons:

✅ **Pros:**
- Works offline
- No need to wait for downloads

❌ **Cons:**
- Large file size (2-5 GB)
- Manual process
- Must repeat when images update

## Option 3: Export Docker Volumes (Database Data)

If you want to preserve your database/data when moving:

### On Current Machine:

1. **Export database** (if you have data you want to keep):
   ```bash
   # Using pg_dump
   docker-compose exec db pg_dump -U postgres pdf_form_filler > database-backup.sql
   
   # Or export the entire volume
   docker run --rm -v pdf-form-filler-saas_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-data.tar.gz /data
   ```

2. **Export storage files** (if needed):
   ```bash
   # Copy storage folder (templates, CSVs, outputs)
   # These are in your project folder under backend/storage (if using bind mounts)
   # OR in Docker volumes (if using named volumes)
   ```

### On New Laptop:

1. **Import database**:
   ```bash
   # Start containers first
   docker-compose up -d db
   
   # Import data
   docker-compose exec -T db psql -U postgres pdf_form_filler < database-backup.sql
   ```

## Recommended Workflow for Travel

### Before Leaving Home:

1. ✅ **Commit and push all code**:
   ```bash
   git add .
   git commit -m "Before travel - latest changes"
   git push
   ```

2. ✅ **Export database backup** (if you have test data):
   ```bash
   docker-compose exec db pg_dump -U postgres pdf_form_filler > database-backup.sql
   ```

3. ✅ **Copy project folder** to laptop (or clone from git):
   ```bash
   # On laptop
   git clone <your-repo-url>
   ```

4. ✅ **Pull Docker images on laptop**:
   ```bash
   cd pdf-form-filler-saas
   docker-compose pull
   ```

5. ✅ **Test that everything works**:
   ```bash
   docker-compose up
   # Verify frontend at http://localhost:3000
   # Verify backend at http://localhost:8000
   ```

### If You Can't Pull Images Before Leaving:

**Option A: Export Images** (see Option 2 above)
- Export images to USB drive
- Load on laptop later

**Option B: Wait Until You Have Internet**
- Copy project folder now
- Pull images when you get internet connection
- First-time setup will require internet

## Complete Setup Script

Here's a script you can run on the laptop to set everything up:

```bash
#!/bin/bash
# setup-laptop.sh

echo "Setting up PDF Form Filler on laptop..."

# 1. Copy or clone project (if not done already)
# git clone <repo-url> or copy folder

# 2. Navigate to project
cd pdf-form-filler-saas

# 3. Copy .env file (if you have one)
# cp .env.example .env
# Edit .env with your settings

# 4. Pull Docker images
echo "Pulling Docker images..."
docker-compose pull

# 5. Build images (if using custom Dockerfiles)
echo "Building images..."
docker-compose build

# 6. Start containers
echo "Starting containers..."
docker-compose up -d

# 7. Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# 8. Import database (if you have backup)
# docker-compose exec -T db psql -U postgres pdf_form_filler < database-backup.sql

echo "Setup complete!"
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
```

## What About Docker Volumes?

Docker volumes (like database data, Redis data) are **also stored separately** from your project folder.

### Your `docker-compose.yml` Uses:

**Named Volumes** (stored in Docker's internal storage):
- `postgres_data` - Database files
- `pgadmin_data` - pgAdmin data

**Bind Mounts** (stored in your project folder):
- `./backend/storage` - Your storage files (templates, CSVs, outputs)
- These **ARE** copied with your project folder! ✅

### To Preserve Database Data:

1. **Export SQL dump** (recommended):
   ```bash
   docker-compose exec db pg_dump -U postgres pdf_form_filler > backup.sql
   ```

2. **Import on new machine**:
   ```bash
   docker-compose up -d db
   docker-compose exec -T db psql -U postgres pdf_form_filler < backup.sql
   ```

## Quick Reference

| Item | Location | Copied with Project? | Action Needed |
|------|----------|---------------------|---------------|
| Source code | Project folder | ✅ Yes | Just copy folder |
| `docker-compose.yml` | Project folder | ✅ Yes | Just copy folder |
| Docker images | Docker storage | ❌ No | Run `docker-compose pull` |
| Database data | Docker volume | ❌ No | Export/import SQL dump |
| Storage files | `backend/storage/` | ✅ Yes (bind mount) | Just copy folder |
| `.env` file | Project folder | ⚠️ Maybe | Copy if exists, or create from `.env.example` |

## Summary

**Minimal Setup (Internet Available):**
1. Copy project folder to laptop
2. Install Docker Desktop
3. Run `docker-compose pull`
4. Run `docker-compose up`

**Complete Setup (With Data):**
1. Copy project folder
2. Export database: `docker-compose exec db pg_dump ... > backup.sql`
3. Copy backup.sql to laptop
4. Install Docker Desktop
5. Run `docker-compose pull`
6. Run `docker-compose up`
7. Import database: `docker-compose exec -T db psql ... < backup.sql`

**Offline Setup:**
1. Export images: `docker save ... -o images.tar`
2. Copy project folder + images.tar to laptop
3. Install Docker Desktop
4. Load images: `docker load -i images.tar`
5. Run `docker-compose up`

The key point: **Just copying the project folder is NOT enough** - you need to pull/build Docker images separately!
