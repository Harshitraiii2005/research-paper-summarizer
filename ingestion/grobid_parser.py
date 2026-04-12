import requests
import xml.etree.ElementTree as ET
from knowledge.schema import PaperKnowledge
from config import GROBID_URL

def parse_with_grobid(pdf_path: str) -> PaperKnowledge:
    """Use GROBID for superior structured extraction"""
    url = f"{GROBID_URL}/api/processFulltextDocument"
    files = {'input': open(pdf_path, 'rb')}
    params = {'consolidateHeader': 1, 'teiCoordinates': 1}
    
    try:
        response = requests.post(url, files=files, params=params, timeout=60)
        response.raise_for_status()
        tei_xml = response.text
    except Exception as e:
        print(f"GROBID failed: {e}. Falling back to PyMuPDF.")
        raise

    root = ET.fromstring(tei_xml)
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    knowledge = PaperKnowledge(
        title=root.find(".//tei:titleStmt/tei:title", ns).text or "Untitled",
        authors=[author.text for author in root.findall(".//tei:author/tei:persName", ns) if author.text],
        abstract=root.find(".//tei:abstract", ns).text or "",
        sections={},
        figures=[],
        tables=[],
        metadata={"parser": "grobid"}
    )
    
    # Sections
    for div in root.findall(".//tei:div", ns):
        heading = div.find(".//tei:head", ns)
        if heading is not None and heading.text:
            sec_name = heading.text.lower().replace(" ", "_")
            content = "".join(div.itertext())
            knowledge.sections[sec_name] = content.strip()
    
    # Figures & Tables (basic extraction)
    for fig in root.findall(".//tei:figure", ns):
        knowledge.figures.append(Figure(caption=fig.text or "", page=1))
    
    print("✅ GROBID parsing complete")
    return knowledge