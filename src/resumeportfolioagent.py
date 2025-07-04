import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END

from src.pdfextractor import PDFExtractor
from src.prompt import SYSTEM_PROMPT
from src.extract_lines import extract_links_from_pdf
from src.models import Portfolio, AgentState

from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# LangGraph Agent Implementation
class ResumePortfolioAgent:
    def __init__(self, google_api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=google_api_key,
            temperature=0.1
        )
        
        # Create the structured output parser
        self.parser = PydanticOutputParser(pydantic_object=Portfolio)
        
        # Initialize the graph
        self.graph = self._create_graph()
        
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        
        # Define the workflow
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("extract_pdf", self._extract_pdf_node)
        workflow.add_node("process_with_llm", self._process_with_llm_node)
        workflow.add_node("validate_output", self._validate_output_node)
        
        # Add edges
        workflow.add_edge("extract_pdf", "process_with_llm")
        workflow.add_edge("process_with_llm", "validate_output")
        workflow.add_edge("validate_output", END)
        
        # Set entry point
        workflow.set_entry_point("extract_pdf")
        
        return workflow.compile()
    
    def _extract_pdf_node(self, state: AgentState) -> AgentState:
        logger.info("Extracting PDF content and links...")
        try:
            if not state.get("pdf_content"):
                return {
                    **state,
                    "status": "error", 
                    "error": "No PDF content provided"
                }

            pdf_bytes = state.get("pdf_bytes")
            if pdf_bytes:
                links = extract_links_from_pdf(pdf_bytes)
            else:
                links = []

            return {
                **state,
                "status": "pdf_extracted",
                "pdf_links": links
            }
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return {
                **state,
                "status": "error",
                "error": f"PDF extraction failed: {str(e)}"
            }

    
    def _process_with_llm_node(self, state: AgentState) -> AgentState:
        """Node to process PDF content with LLM"""
        logger.info("Processing content with LLM...")
        try:
            system_message = SYSTEM_PROMPT
            
            links_text = "\n".join(state.get("pdf_links", []))
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=f"Resume content:\n\n{state.get('pdf_content', '')}\n\nDetected links:\n{links_text}")
            ]
            
            # Use structured output
            structured_llm = self.llm.with_structured_output(Portfolio)
            result = structured_llm.invoke(messages)
            
            return {
                **state,
                "status": "llm_processed",
                "extracted_data": result
            }
            
        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            return {
                **state,
                "status": "error",
                "error": f"LLM processing failed: {str(e)}"
            }
    
    def _validate_output_node(self, state: AgentState) -> AgentState:
        """Node to validate the extracted data"""
        logger.info("Validating extracted data...")
        try:
            extracted_data = state.get("extracted_data")
            if not extracted_data:
                return {
                    **state,
                    "status": "error",
                    "error": "No data extracted"
                }
            
            if state.get("pdf_links"):
                extracted_data.pdfLinks = state.get("pdf_links")
            
            # Additional validation can be added here
            return {
                **state,
                "status": "completed",
                "extracted_data": extracted_data
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                **state,
                "status": "error",
                "error": f"Validation failed: {str(e)}"
            }
    
    async def process_resume(self, pdf_bytes: bytes) -> Portfolio:
        """Process resume PDF and extract structured data"""
        try:
            # Extract text from PDF
            pdf_text = PDFExtractor.extract_text(pdf_bytes)
            
            if not pdf_text:
                raise ValueError("Could not extract text from PDF")
            
            # Initialize state
            initial_state: AgentState = {
                "pdf_content": pdf_text,
                "pdf_bytes": pdf_bytes,
                "extracted_data": None,
                "pdf_links": None,
                "error": None,
                "status": "initialized"
            }
            
            # Run the graph
            final_state = self.graph.invoke(initial_state)
            
            if final_state.get("status") == "error":
                raise ValueError(final_state.get("error", "Unknown error"))
            
            extracted_data = final_state.get("extracted_data")
            if not extracted_data:
                raise ValueError("No data was extracted from the resume")
                
            return extracted_data
            
        except Exception as e:
            logger.error(f"Resume processing failed: {e}")
            raise HTTPException(status_code=500, detail=f"Resume processing failed: {str(e)}")
