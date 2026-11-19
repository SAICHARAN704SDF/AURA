"""Install English OCR data from official Tesseract data with a pinned checksum."""
from pathlib import Path
import hashlib
import urllib.request

TARGET=Path.home()/'.cache/aura/tessdata/eng.traineddata'
SHA256='7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'

def main():
    url='https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/eng.traineddata'
    with urllib.request.urlopen(url,timeout=45) as response:data=response.read(5*1024*1024)
    if hashlib.sha256(data).hexdigest()!=SHA256:raise RuntimeError('OCR data checksum mismatch')
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    TARGET.write_bytes(data)
    print('English OCR language data installed:',TARGET)

if __name__=='__main__':main()
