from io import BytesIO
import PyPDF2, logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PDF extraction utilities
class PDFExtractor:
    @staticmethod
    def extract_with_pypdf2(pdf_bytes: bytes) -> str:
        """Extract text using PyPDF2"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return ""

    @staticmethod
    def extract_text(pdf_bytes: bytes) -> str:
        """Extract text using multiple methods for better reliability"""
        text = PDFExtractor.extract_with_pypdf2(pdf_bytes)        
        return text