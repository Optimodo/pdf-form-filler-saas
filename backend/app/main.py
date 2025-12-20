from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.pdf_routes import router as pdf_router
from .api.auth_routes import router as auth_router
from .api.admin_routes import router as admin_router
from .database import create_db_and_tables, get_async_session
from .core.user_limits import refresh_tier_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup and refresh tier cache."""
    await create_db_and_tables()
    # Refresh tier cache from database
    async for session in get_async_session():
        try:
            await refresh_tier_cache(session)
        except Exception as e:
            # If table doesn't exist yet or no tiers, that's okay - cache will use fallbacks
            print(f"Note: Could not refresh tier cache on startup: {e}")
        break
    yield


app = FastAPI(
    title="PDF Form Filler SaaS",
    description="Web-based PDF form filling application with user authentication",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth_router, prefix="/api")
app.include_router(pdf_router)
app.include_router(admin_router)  # Admin routes already have /api/admin prefix

@app.get("/")
async def root():
    return {"message": "PDF Form Filler SaaS API with Authentication", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pdf-form-filler-saas"}


