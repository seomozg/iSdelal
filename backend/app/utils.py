import re
from bs4 import BeautifulSoup

def html_to_text(html: str) -> str:
    print(f"🌐 Processing HTML content, length: {len(html)}")

    soup = BeautifulSoup(html, 'html.parser')

    # Log what we're removing
    scripts = soup.find_all(['script', 'style', 'noscript'])
    print(f"🗑️ Removing {len(scripts)} script/style/noscript elements")

    for s in scripts:
        s.decompose()

    text = soup.get_text(separator=' ', strip=True)

    print(f"📄 Raw extracted text length: {len(text)}")
    print(f"📄 First 500 chars: {text[:500][:100]}...")  # First 100 meaningful chars

    # Count words before cleaning
    words_before = len(text.split())

    text = re.sub(r"\s+", ' ', text)

    # Count words after cleaning
    words_after = len(text.split())

    print(f"🔤 Word count: {words_after} (before cleaning: {words_before})")

    # Log if text is suspicious
    if words_after < 10:
        print(f"⚠️ Very few words extracted! HTML might be mostly images/videos or protected content")

    return text

def chunk_text(text: str, chunk_size: int = 50, overlap: int = 10):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = ' '.join(words[i:i+chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks
