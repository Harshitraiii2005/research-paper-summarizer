from pptx import Presentation
from pptx.util import Inches, Pt
from knowledge.schema import PaperKnowledge
import os

def generate_ppt(paper: PaperKnowledge, summary: str, flaws: str, comparison: str, filename: str = "paper_presentation.pptx"):
    prs = Presentation()
    
    # Title slide
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = paper.title
    slide.placeholders[1].text = ", ".join(paper.authors[:3])
    
    # Summary slide
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Key Summary"
    tf = slide.placeholders[1].text_frame
    tf.text = summary[:800]
    
    # Flaws slide
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Methodology Flaws & Limitations"
    tf = slide.placeholders[1].text_frame
    tf.text = flaws
    
    # Comparison slide
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Comparison with Similar Papers"
    tf = slide.placeholders[1].text_frame
    tf.text = comparison[:1000]
    
    # TL;DR slide
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "TL;DR"
    tf = slide.placeholders[1].text_frame
    tf.text = summary.split("\n")[0]
    
    prs.save(filename)
    print(f"✅ PPT saved: {filename}")
    return filename