from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PDF Form Filler SaaS",
    description="Web-based PDF form filling application",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "PDF Form Filler SaaS API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pdf-form-filler-saas"}

@app.get("/api/templates")
async def list_templates():
    """List available PDF templates"""
    return {
        "templates": [
            {"id": "electrical", "name": "Electrical", "category": "Building Services"},
            {"id": "fire-detection", "name": "Fire Detection", "category": "Safety"},
            {"id": "hiu-fcu", "name": "HIU FCU", "category": "HVAC"},
            {"id": "hiu-rad", "name": "HIU RAD", "category": "HVAC"},
            {"id": "irs-data", "name": "IRS Data", "category": "Data"},
            {"id": "mvhr", "name": "MVHR", "category": "Ventilation"}
        ]
    }

