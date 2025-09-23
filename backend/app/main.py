from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.pdf_routes import router as pdf_router
from .api.auth_routes import router as auth_router
from .database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    await create_db_and_tables()
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

@app.get("/")
async def root():
    return {"message": "PDF Form Filler SaaS API with Authentication", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pdf-form-filler-saas"}


