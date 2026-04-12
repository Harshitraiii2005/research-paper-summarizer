import arxiv
import requests
from pathlib import Path

def download_arxiv_paper(arxiv_input: str, save_dir: str = "papers") -> str:
    Path(save_dir).mkdir(exist_ok=True)
    if "arxiv.org" in arxiv_input:
        paper_id = arxiv_input.split("/")[-1].replace(".pdf", "")
    else:
        paper_id = arxiv_input.strip()
    
    search = arxiv.Search(id_list=[paper_id])
    paper = next(search.results())
    pdf_url = paper.pdf_url
    filename = f"{paper_id.replace('/', '_')}.pdf"
    filepath = Path(save_dir) / filename
    
    print(f"📥 Downloading: {paper.title}")
    response = requests.get(pdf_url)
    filepath.write_bytes(response.content)
    print(f"✅ Saved: {filepath}")
    return str(filepath)