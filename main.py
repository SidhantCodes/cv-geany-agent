import os, logging, uvicorn

# FastAPI imports
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# Pydantic Models
from src.models import Portfolio
from src.resumeportfolioagent import ResumePortfolioAgent


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# FastAPI Application
app = FastAPI(
    title="Resume to Portfolio AI Agent",
    description="AI-powered resume parser that extracts structured portfolio data",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")

agent = ResumePortfolioAgent(GOOGLE_API_KEY)

@app.post("/upload-resume", response_model=Portfolio)
async def upload_resume(file: UploadFile = File(...)):
    """Upload and process a resume PDF"""

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        pdf_bytes = await file.read()
        result = await agent.process_resume(pdf_bytes)
        return result
        
    except Exception as e:
        logger.error(f"Upload processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__": 
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )