"""
FILE: backend/src/aura/rag/ingestion/documents.py
PURPOSE: Validate uploads and extract native text or supported local OCR text.
MAIN RESPONSIBILITY: Document Parsing.
INPUTS: Filename and up to 5 MB of file bytes.
OUTPUTS: Document with pages, content hash and stable identity.
IMPORTANT FUNCTIONS / CLASSES: Page, Document, Chunk, digest, load.
CONNECTED MODULES: aura.observability.events, aura.core.
WHERE THIS FILE IS USED: backend/src/aura/rag/pipeline.py, backend/src/aura/rag/embeddings/cache.py, backend/src/aura/rag/chunking/chunker.py, backend/src/aura/rag/generation/answers.py, backend/src/aura/rag/vectorstore/qdrant_store.py.
PRESENTATION EXPLANATION: "Extraction preserves page identity so later evidence can be traced back to its source."
"""
# PRESENTATION SECTION: DOCUMENT PARSING
from aura.observability.events import traced, emit, span
import csv, hashlib, io, re, uuid
from pathlib import PurePath
from html.parser import HTMLParser
from pydantic import BaseModel, Field
from aura.core import ServiceError

class Page(BaseModel):
    number: int | None = None
    text: str
    requires_ocr: bool = False
    ocr_applied: bool = False

class Document(BaseModel):
    id: str
    filename: str
    content_hash: str
    source_url: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    pages: list[Page]

class Chunk(BaseModel):
    id: str
    document_id: str
    filename: str
    page: int | None
    start: int
    end: int
    text: str
    content_hash: str

def digest(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

class HTMLText(HTMLParser):
    """Extract text from an uploaded HTML snapshot without rendering or fetching it."""

    ignored = {"head", "nav", "footer", "aside", "script", "style", "template", "noscript"}
    blocks = {"p", "div", "section", "article", "li", "br", "h1", "h2", "h3", "td", "tr"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = []
        self.metadata = {}
        self.title_parts = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.in_title = True
        if tag == 'meta':
            values = dict(attrs)
            key = (values.get('name') or values.get('property') or '').lower()
            fields = {'citation_title':'title','citation_author':'author','citation_doi':'doi',
                      'citation_publication_date':'publication_date','dc.date':'publication_date',
                      'dc.description':'abstract','citation_abstract':'abstract','og:title':'title'}
            content = (values.get('content') or '').strip()
            if key in fields and content:
                field = fields[key]
                if field == 'author' and field in self.metadata:
                    content = self.metadata[field] + '; ' + content
                self.metadata[field] = content[:3000]
        if tag in self.ignored:
            self.hidden.append(tag)
        elif not self.hidden and tag in self.blocks:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        elif not self.hidden and tag in self.blocks:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if not self.hidden:
            self.parts.append(data)

    def text(self):
        return "\n".join(clean for line in "".join(self.parts).splitlines()
                         if (clean := " ".join(line.split())))


@traced('parsing')
def load(filename: str, data: bytes) -> Document:
    """Purpose: Document extraction.
    
    Inputs: Filename and raw bytes.
    Process and rationale: Validate type/size/name, extract PDF or UTF-8 text, normalize CSV or call local OCR for supported images; compute content-derived identity.
    Returns: Document containing source pages and OCR flags.
    """
    if not data or len(data)>5*1024*1024: raise ServiceError('invalid_file_size')
    if PurePath(filename).name!=filename or '\\' in filename: raise ServiceError('invalid_filename')
    ext=PurePath(filename).suffix.lower()
    pages=[]
    metadata={}
    if ext=='.pdf':
        import pymupdf
        try:
            with pymupdf.open(stream=data,filetype='pdf') as pdf:
                if pdf.needs_pass or len(pdf)>200: raise ServiceError('invalid_pdf')
                metadata={key:value for key,value in pdf.metadata.items() if key in ('title','author','creationDate','subject') and value}
                ocr_pages=0
                for i,p in enumerate(pdf):
                    text=p.get_text()
                    applied=False
                    if len(text.strip())<20 and p.get_images():
                        from .ocr import extract
                        ocr_pages+=1
                        if ocr_pages>20:raise ServiceError('ocr_page_limit')
                        text=extract(p);applied=True
                    pages.append(Page(number=i+1,text=text,requires_ocr=len(text.strip())<20,ocr_applied=applied))
        except ServiceError: raise
        except Exception: raise ServiceError('invalid_pdf') from None
    elif ext in ('.png','.jpg','.jpeg'):
        import pymupdf
        from .ocr import extract
        try:
            with pymupdf.open(stream=data) as image:
                if image.metadata.get('format')!='Image':raise ServiceError('invalid_image')
                page=image[0]
                if page.rect.width*page.rect.height>10_000_000:raise ServiceError('ocr_page_size_limit')
                with pymupdf.open(stream=image.convert_to_pdf(),filetype='pdf') as pdf:
                    text=extract(pdf[0])
            pages=[Page(number=1,text=text,requires_ocr=len(text.strip())<20,ocr_applied=True)]
        except ServiceError:raise
        except Exception:raise ServiceError('invalid_image') from None
    elif ext == '.docx':
        import zipfile
        from defusedxml.ElementTree import fromstring
        ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entry = archive.getinfo('word/document.xml')
                if entry.file_size > 8_000_000:
                    raise ServiceError('extracted_text_limit')
                root = fromstring(archive.read(entry))
                paragraphs = [''.join(el.text or '' for el in p.iter(ns+'t')) for p in root.iter(ns+'p')]
                pages = [Page(text='\n'.join(paragraphs))]
                if 'docProps/core.xml' in archive.namelist():
                    core = archive.getinfo('docProps/core.xml')
                    if core.file_size <= 100_000:
                        props = fromstring(archive.read(core))
                        names = {'title':'title','creator':'author','created':'creationDate','description':'description'}
                        for node in props:
                            key = node.tag.split('}')[-1]
                            if key in names and node.text:
                                metadata[names[key]] = node.text[:2000]
        except ServiceError:
            raise
        except Exception:
            raise ServiceError('invalid_docx') from None
    elif ext in ('.txt','.md','.csv','.html','.htm'):
        try: text=data.decode('utf-8-sig')
        except UnicodeError: raise ServiceError('invalid_encoding') from None
        if '\x00' in text: raise ServiceError('invalid_text')
        if ext in ('.html', '.htm'):
            parser = HTMLText()
            parser.feed(text)
            parser.close()
            text = parser.text()
            metadata.update(parser.metadata)
            if parser.title_parts:
                metadata.setdefault('title',' '.join(''.join(parser.title_parts).split())[:500])
        if ext=='.csv':
            try:
                rows=list(csv.reader(io.StringIO(text),strict=True))
                if not rows or any(len(r)!=len(rows[0]) for r in rows): raise ValueError()
                text='\n'.join(' | '.join(r) for r in rows)
            except (csv.Error,ValueError): raise ServiceError('invalid_csv') from None
        pages=[Page(text=text)]
    else: raise ServiceError('unsupported_file_type')
    if sum(len(p.text) for p in pages)>1_000_000: raise ServiceError('extracted_text_limit')
    # Only the first page is examined for author-supplied bibliographic labels.
    # A DOI in a bibliography or arbitrary passage could refer to a different paper.
    if pages:
        if found := re.search(r'(?im)^\s*doi\s*:\s*(10\.\d{4,9}/[^\s]+)', pages[0].text):
            metadata.setdefault('doi',found[1].rstrip('.,;'))
        if found := re.search(r'(?ims)^\s*abstract[ \t:.-]*(?:\n|\s)(.+?)(?=\n\s*\n|\n\s*(?:1[.]?\s+)?Introduction\b|\Z)', pages[0].text):
            metadata.setdefault('abstract',' '.join(found[1].split())[:3000])
    h=digest(data)
    return Document(id=str(uuid.uuid5(uuid.NAMESPACE_URL,h)),filename=filename,content_hash=h,pages=pages,metadata=metadata)
