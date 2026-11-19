"""
FILE: backend/src/aura/rag/ingestion/ocr.py
PURPOSE: Read image-only pages using PyMuPDF and English Tesseract language data.
MAIN RESPONSIBILITY: Local Ocr.
INPUTS: A PyMuPDF page and installed eng.traineddata.
OUTPUTS: Recognized text or a bounded OCR error.
IMPORTANT FUNCTIONS / CLASSES: tessdata, status, extract.
CONNECTED MODULES: aura.core, aura.observability.events.
WHERE THIS FILE IS USED: Imported by its feature package, application composition or tests.
PRESENTATION EXPLANATION: "OCR reads pixels locally; it uses no generative-model tokens and can misread handwriting."
"""
# PRESENTATION SECTION: LOCAL OCR
import os
from pathlib import Path
import subprocess
import sys
from aura.core import ServiceError
from aura.observability.events import span


def tessdata():
    root=Path(os.environ.get('TESSDATA_PREFIX',str(Path.home()/'.cache/aura/tessdata')))
    return root if (root/'eng.traineddata').is_file() else None


def status():
    return 'local_english' if tessdata() else 'unavailable_missing_language_data'


def extract(page):
    """Purpose: Scanned document OCR.
    
    Inputs: PyMuPDF page.
    Process and rationale: Locate English language data, render bounded pixels and run PyMuPDF/Tesseract in a subprocess with a 25-second timeout.
    Returns: Recognized text; missing data, timeout and size errors remain explicit.
    """
    root=tessdata()
    if root is None:raise ServiceError('ocr_language_data_missing')
    if page.rect.width*page.rect.height*4>10_000_000:raise ServiceError('ocr_page_size_limit')
    import pymupdf
    with span('ocr',page=page.number+1,engine='tesseract_local',language='eng'):
        png=page.get_pixmap(matrix=pymupdf.Matrix(2,2),colorspace=pymupdf.csRGB,alpha=False).tobytes('png')
        script="""import sys,pymupdf
pix=pymupdf.Pixmap(sys.stdin.buffer.read())
with pymupdf.open(stream=pix.pdfocr_tobytes(language='eng',tessdata=sys.argv[1]),filetype='pdf') as doc:
 sys.stdout.buffer.write(doc[0].get_text().encode('utf-8'))
"""
        try:
            result=subprocess.run([sys.executable,'-c',script,str(root)],input=png,capture_output=True,timeout=25,check=True)
        except subprocess.TimeoutExpired:raise ServiceError('ocr_timeout') from None
        except subprocess.CalledProcessError:raise ServiceError('ocr_failed') from None
        if len(result.stdout)>1_000_000:raise ServiceError('ocr_text_limit')
        return result.stdout.decode('utf-8')
