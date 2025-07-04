# extract_pdf_links.py

from typing import TypedDict, List
from langgraph.graph import StateGraph
import fitz  # PyMuPDF

# --- 1. Define the function to extract links from a PDF ---
def extract_links_from_pdf(pdf_path: str) -> List[str]:
    doc = fitz.open(pdf_path)
    links = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        annotations = page.get_links()
        for annot in annotations:
            if 'uri' in annot:
                links.append(annot['uri'])

    doc.close()
    return links

# --- 2. Define the LangGraph state ---
class LinkExtractionState(TypedDict):
    pdf_path: str
    links: List[str]

# --- 3. Create a LangGraph node to extract the links ---
def extract_links_node(state: LinkExtractionState) -> LinkExtractionState:
    links = extract_links_from_pdf(state["pdf_path"])
    return {**state, "links": links}

# --- 4. Create and run the LangGraph workflow ---
def main(pdf_path: str):
    # Build the graph
    workflow = StateGraph(LinkExtractionState)
    workflow.add_node("extract_links", extract_links_node)
    workflow.set_entry_point("extract_links")
    workflow.set_finish_point("extract_links")

    # Compile and run
    app = workflow.compile()
    result = app.invoke({"pdf_path": pdf_path})
    print("📎 Extracted links:")
    for link in result["links"]:
        print(link)

# --- 5. Run the script ---
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python extract_pdf_links.py <path_to_pdf>")
    else:
        main(sys.argv[1])
