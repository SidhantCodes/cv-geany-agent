import os, logging, uvicorn, io
from dotenv import load_dotenv

# FastAPI imports
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Pydantic Models
from src.models import Portfolio
from src.resumeportfolioagent import ResumePortfolioAgent
from src.portfolio_generator import PortfolioGenerator

load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# FastAPI Application
app = FastAPI(
    title="CVGeany Server",
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


GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

try:
    portfolio_generator = PortfolioGenerator(
        github_repo=GITHUB_REPO,
        github_token=GITHUB_TOKEN,
        branch="master"
    )
except (ValueError, TypeError) as e:
    logger.warning(f"PortfolioGenerator not initialized: {e}. Download endpoint will not be available.")
    portfolio_generator = None


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


@app.post("/generate-portfolio")
async def generate_portfolio(portfolio_data: Portfolio):
    """
    Accepts portfolio JSON, combines it with a GitHub repo template,
    and returns a downloadable zip file.
    """
    if not portfolio_generator:
        raise HTTPException(
            status_code=503, 
            detail="Portfolio generation service is not configured on the server."
        )

    try:
        logger.info(f"Received request to generate portfolio for {portfolio_data.name}")
        zip_bytes = portfolio_generator.generate_zip(portfolio_data)

        safe_name = "".join(c for c in portfolio_data.name if c.isalnum() or c in (' ', '.')).rstrip()
        filename = f"{safe_name}_portfolio.zip".replace(" ", "_")

        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Portfolio generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate portfolio package: {str(e)}")


if __name__ == "__main__": 
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )