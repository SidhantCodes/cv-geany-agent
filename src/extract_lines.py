import fitz, logging
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_links_from_pdf(pdf_bytes: bytes) -> List[str]:
    links = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            annotations = doc[page_num].get_links()
            for annot in annotations:
                if "uri" in annot:
                    links.append(annot["uri"])
        doc.close()
    except Exception as e:
        logger.error(f"Link extraction failed: {e}")
    return links