"""
Prompt Injection Defense & Untrusted Content Sanitizer.
Ensures external web and news content cannot inject instructions into LLM system prompts.
"""

import re


ADVERSARIAL_PATTERNS = [
    r'(?i)ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions',
    r'(?i)you\s+are\s+now\s+a',
    r'(?i)system\s*:\s*',
    r'(?i)as\s+an\s+ai\s+language\s+model',
    r'(?i)prompt\s+injection',
    r'(?i)override\s+(?:system|developer)\s+prompt',
    r'(?i)bütün\s+önceki\s+talimatları\s+unut',
    r'(?i)artık\s+sen\s+bir',
]


def sanitize_external_text(text: str) -> str:
    """Neutralizes known adversarial injection phrases."""
    cleaned = text
    for pat in ADVERSARIAL_PATTERNS:
        cleaned = re.sub(pat, '[UNTRUSTED_DIRECTIVE_REMOVED]', cleaned)
    return cleaned


def wrap_untrusted_data(data_content: str) -> str:
    """Wraps news content into strict data isolation delimiters."""
    safe_data = sanitize_external_text(data_content)
    return f"""
<UNTRUSTED_MARKET_DATA>
{safe_data}
</UNTRUSTED_MARKET_DATA>
""".strip()
