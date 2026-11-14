"""Bounded extraction and source-preserving recursive chunking."""
from aura.observability.events import traced, emit, span
import csv, hashlib, io, re, uuid
from pathlib import PurePath
from pydantic import BaseModel, Field
from aura.core import ServiceError

class Page(BaseModel):
    number: int | None = None
    text: str
    requires_ocr: bool = False

class Document(BaseModel):
    id: str
    filename: str
    content_hash: str
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

@traced('parsing')
def load(filename: str, data: bytes) -> Document:
    if not data or len(data)>5*1024*1024: raise ServiceError('invalid_file_size')
    if PurePath(filename).name!=filename or '\\' in filename: raise ServiceError('invalid_filename')
    ext=PurePath(filename).suffix.lower()
    pages=[]
    if ext=='.pdf':
        import pymupdf
        try:
            with pymupdf.open(stream=data,filetype='pdf') as pdf:
                if pdf.needs_pass or len(pdf)>200: raise ServiceError('invalid_pdf')
                for i,p in enumerate(pdf):
                    text=p.get_text()
                    pages.append(Page(number=i+1,text=text,requires_ocr=len(text.strip())<20))
        except ServiceError: raise
        except Exception: raise ServiceError('invalid_pdf') from None
    elif ext in ('.txt','.md','.csv'):
        try: text=data.decode('utf-8-sig')
        except UnicodeError: raise ServiceError('invalid_encoding') from None
        if '\x00' in text: raise ServiceError('invalid_text')
        if ext=='.csv':
            try:
                rows=list(csv.reader(io.StringIO(text),strict=True))
                if not rows or any(len(r)!=len(rows[0]) for r in rows): raise ValueError()
                text='\n'.join(' | '.join(r) for r in rows)
            except (csv.Error,ValueError): raise ServiceError('invalid_csv') from None
        pages=[Page(text=text)]
    else: raise ServiceError('unsupported_file_type')
    if sum(len(p.text) for p in pages)>1_000_000: raise ServiceError('extracted_text_limit')
    h=digest(data)
    return Document(id=str(uuid.uuid5(uuid.NAMESPACE_URL,h)),filename=filename,content_hash=h,pages=pages)
