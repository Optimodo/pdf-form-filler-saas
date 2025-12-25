# Docker Data Storage - Where Everything Lives

## Quick Answer

**Docker images**: Built/downloaded from instructions in your project folder, but stored in Docker's internal storage (NOT in project folder)

**Database data**: Stored in Docker volume (NOT in project folder) - it's a separate named volume

**Storage files** (templates, CSVs, outputs): Stored in your project folder (`backend/storage/`) - this IS copied with your project ✅

## Detailed Breakdown

### 1. Docker Images - Where Do They Come From?

#### `docker-compose pull`
Downloads pre-built images from Docker Hub:
- `postgres:15` → Downloaded from Docker Hub
- `redis:7-alpine` → Downloaded from Docker Hub  
- `dpage/pgadmin4:latest` → Downloaded from Docker Hub

**Source**: Docker Hub (internet)

#### `docker-compose build`
Builds images using instructions in your project folder:
- `backend` image → Built from `backend/Dockerfile` (instructions in your project folder)
- `frontend` image → Built from `frontend/Dockerfile` (instructions in your project folder)

**Source**: Your project folder (Dockerfiles)

#### Where Images Are Stored After Building/Pulling?
- **Location**: Docker's internal storage (`C:\ProgramData\docker` on Windows)
- **NOT in your project folder** ❌

### 2. Database Schema vs Database Data

#### Database Schema (Table Structure)
**Created automatically by your application code:**
- When backend starts, `create_db_and_tables()` runs (from `backend/app/main.py`)
- It reads your models from `backend/app/models.py`
- Creates all tables automatically using SQLAlchemy's `Base.metadata.create_all`

**Source**: Your project folder (Python code) ✅

#### Database Data (Actual Records)
**Stored in Docker volume `postgres_data`:**

Looking at your `docker-compose.yml`:
```yaml
db:
  image: postgres:15
  volumes:
    - postgres_data:/var/lib/postgresql/data  # ← Named volume
```

This creates a **named Docker volume** called `postgres_data`.

**Where is it stored?**
- Docker's internal volume storage (NOT in your project folder) ❌
- Windows: `\\wsl$\docker-desktop-data\data\docker\volumes\pdf-form-filler-saas_postgres_data`
- Mac/Linux: `/var/lib/docker/volumes/pdf-form-filler-saas_postgres_data`

**What this means:**
- ✅ Database schema is recreated automatically (from your code)
- ❌ Database data (users, jobs, etc.) is NOT copied with project folder
- ✅ You start with empty database on new machine (unless you export/import)

### 3. Storage Files (Templates, CSVs, PDFs)

Looking at your `docker-compose.yml`:
```yaml
backend:
  volumes:
    - ./backend:/app                    # Source code (bind mount)
    - ./backend/storage:/app/storage    # Storage files (bind mount) ← This one!
```

This uses a **bind mount** - directly maps a folder in your project to the container.

**Where is it stored?**
- `./backend/storage/` in your project folder ✅
- This IS copied with your project folder! ✅

**What's in there:**
- Templates (PDFs)
- CSV files
- Generated PDF outputs
- ZIP files

## Visual Representation

```
Your Project Folder (pdf-form-filler-saas/)
├── backend/
│   ├── Dockerfile              ← Instructions to build backend image
│   ├── storage/                ← ✅ STORED HERE (copied with project)
│   │   ├── templates/
│   │   ├── csv_files/
│   │   └── outputs/
│   └── app/
│       └── models.py           ← Database schema definitions
├── frontend/
│   └── Dockerfile              ← Instructions to build frontend image
└── docker-compose.yml          ← Instructions for docker-compose

Docker's Internal Storage (NOT in project folder)
├── Images (from docker-compose pull/build)
│   ├── postgres:15
│   ├── redis:7-alpine
│   ├── pdf-form-filler-saas-backend
│   └── pdf-form-filler-saas-frontend
└── Volumes (database data)
    └── postgres_data/          ← ❌ Database data stored here (NOT copied)
        └── (all your database files)
```

## What Happens on New Laptop?

### Step-by-Step:

1. **Copy project folder** → ✅ Gets:
   - Source code
   - Dockerfiles (instructions)
   - `docker-compose.yml` (instructions)
   - `backend/storage/` (your files) ✅
   - **But NOT database data** ❌

2. **Run `docker-compose pull`** → Downloads:
   - `postgres:15` from Docker Hub
   - `redis:7-alpine` from Docker Hub
   - `dpage/pgadmin4:latest` from Docker Hub

3. **Run `docker-compose build`** → Builds:
   - `backend` image (uses `backend/Dockerfile` from project folder)
   - `frontend` image (uses `frontend/Dockerfile` from project folder)

4. **Run `docker-compose up`** → Creates:
   - Containers from images
   - New empty `postgres_data` volume (empty database!)
   - Maps `backend/storage/` from project folder ✅

5. **Backend starts** → Automatically:
   - Connects to PostgreSQL
   - Runs `create_db_and_tables()` (from `backend/app/main.py`)
   - Creates all tables from your models ✅
   - Database is empty but schema exists ✅

### Result on New Laptop:

✅ **Schema**: Created automatically (from your code)
✅ **Storage files**: Already there (from project folder)
❌ **Database data**: Empty (users, jobs, etc. are gone unless you export/import)

## To Preserve Database Data

### Export from Current Machine:
```bash
docker-compose exec db pg_dump -U postgres pdf_form_filler > database-backup.sql
```

This creates a SQL file with all your data.

### Import on New Laptop:
```bash
# After docker-compose up (so database exists)
docker-compose exec -T db psql -U postgres pdf_form_filler < database-backup.sql
```

## Summary Table

| Item | Where Instructions Are | Where Data Is Stored | Copied with Project? |
|------|----------------------|---------------------|---------------------|
| **Backend image** | `backend/Dockerfile` (in project) | Docker storage | ❌ No (instructions copied, image built) |
| **Frontend image** | `frontend/Dockerfile` (in project) | Docker storage | ❌ No (instructions copied, image built) |
| **PostgreSQL image** | Docker Hub (pulled) | Docker storage | ❌ No (downloaded) |
| **Database schema** | `backend/app/models.py` (in project) | Created in database | ✅ Yes (code copied, schema created on startup) |
| **Database data** | Created by app usage | Docker volume `postgres_data` | ❌ No (export/import needed) |
| **Storage files** | Created by app usage | `backend/storage/` (bind mount) | ✅ Yes (folder copied) |

## Answer to Your Questions

### Q: "docker-compose pull/build/up will get the docker data from where?"

**A:** 
- `pull` → Downloads from Docker Hub (internet)
- `build` → Uses Dockerfiles from your project folder
- `up` → Uses images (from pull/build) to create containers

### Q: "it will use the instructions in the project folder to create the images on the laptop?"

**A:** Yes! 
- `build` reads `backend/Dockerfile` and `frontend/Dockerfile` from your project folder
- Creates images on the laptop using those instructions
- Images are stored in Docker's internal storage (not in project folder)

### Q: "we need the database to be setup i thought postgres database and data was stored within the project folder also?"

**A:** Partially correct:
- ✅ **Database schema**: Created automatically from your code (in project folder)
- ❌ **Database data**: Stored in Docker volume (NOT in project folder)
- ✅ **Storage files**: Stored in `backend/storage/` (IS in project folder)

**What you need to do:**
1. Copy project folder ✅
2. Run `docker-compose pull` and `build` ✅
3. Run `docker-compose up` (creates empty database with correct schema) ✅
4. Optionally export/import database data if you need test data ✅

## The Good News

Your setup automatically creates the database schema on startup, so you don't need to manually set up tables! The database will be empty, but all the tables will exist and be ready to use.
