import re
import tiktoken
try:
    import nltk
    from nltk.corpus import stopwords
    # Ensure stopwords are downloaded
    nltk.download('stopwords', quiet=True)
    STOPWORDS = set(stopwords.words('english'))
except ImportError:
    STOPWORDS = set()

FILLER_PHRASES = [
    "please can you",
    "i was wondering if you could",
    "would you mind",
    "can you",
    "could you",
    "please",
    "i would like to know",
    "tell me",
]

def compress_prompt(text: str) -> tuple[str, float]:
    """
    Compresses a prompt by removing redundant whitespace, filler phrases, and optional stopwords.
    Returns a tuple of (compressed_text, compression_ratio).
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    original_tokens = len(encoding.encode(text))
    
    if original_tokens == 0:
        return text, 1.0

    # Technique 1: Heuristic - Remove filler phrases
    compressed_text = text
    lower_text = compressed_text.lower()
    
    # We do a simple case-insensitive replace for filler phrases
    for phrase in sorted(FILLER_PHRASES, key=len, reverse=True):
        # Use regex for case-insensitive replacement with word boundaries
        pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
        compressed_text = pattern.sub("", compressed_text)
        
    # Technique 2: Stopwords
    if STOPWORDS:
        words = compressed_text.split()
        filtered_words = [w for w in words if w.lower() not in STOPWORDS]
        compressed_text = " ".join(filtered_words)

    # Remove redundant whitespace and newlines
    compressed_text = re.sub(r'\s+', ' ', compressed_text).strip()
    
    compressed_tokens = len(encoding.encode(compressed_text))
    
    # Avoid division by zero
    if compressed_tokens == 0:
        return compressed_text, float(original_tokens)
        
    compression_ratio = original_tokens / compressed_tokens
    return compressed_text, compression_ratio
