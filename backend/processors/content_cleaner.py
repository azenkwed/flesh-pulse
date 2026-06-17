"""Shared text-cleaning utilities applied before DB storage and at display time."""
import re

# Matches a full line (HTML tags stripped) that is a scraping artifact, not article content.
_BOILERPLATE_RE = re.compile(
    r"^("
    # Image / media viewer UI
    r"click\s+(?:to\s+)?expand\b.*"
    r"|tap\s+(?:to\s+)?expand\b.*"
    # Audio / video player controls
    r"|0:\d{2}"                          # "0:00"
    r"|/\s*\d+:\d{2}"                   # "/ 1:50"
    r"|\d+\s*[×xX]"                     # "1×", "2x" (playback speed)
    # Single-letter dropcap scraped as its own line
    r"|[a-zA-Z]"
    # Newsletter / subscription prompts
    r"|subscribe(?:\s+now)?"
    r"|join\s+the\s+newsletter\b.*"
    r"|become\s+a\s+(?:paid\s+)?subscriber\b.*"
    r"|sign\s+up\s+for\s+(?:our\s+)?newsletter\b.*"
    r"|if\s+you\s+become\s+a\s+(?:paid\s+)?subscriber\b.*"
    r"|listen\s+to\s+the\s+(?:weekly\s+)?podcast\b.*"
    r"|subscribe\s+to\s+(?:read|access|continue)\b.*"
    r"|(?:this\s+article\s+is\s+)?for\s+(?:paid\s+)?subscribers?\s+only\b.*"
    # Form feedback
    r"|success"
    r"|error"
    r"|great!\s+check\s+your\s+inbox\b.*"
    r"|please\s+enter\s+a\s+valid\s+email\b.*"
    # Navigation / content discovery labels
    r"|read\s+more\.?"
    r"|continue\s+reading\.?"
    r"|also\s+read\s*:?.*"
    r"|also\s+see\s*:?.*"
    r"|related\s*:?"
    r"|see\s+also\s*:?.*"
    r"|advertisement"
    r"|sponsored(?:\s+content)?"
    # Document download links
    r"|download\s+(?:in\s+)?(?:english|arabic|french|spanish|pdf|report).*"
    # Photo captions and image credits
    r"|©\s*\d{4}\b.*"
    r"|copyright\s+\d{4}\b.*"
    r"|\(c\)\s*\d{4}\b.*"
    r"|photo\s*(?:credit|by)\s*:.*"
    r"|image\s*(?:credit|by|source)\s*:.*"
    r"|(?:ap|afp|epa|reuters|getty\s+images?|shutterstock|alamy)\s*/.*"
    r"|\w[\w\s]*\s*/\s*(?:ap|afp|epa|reuters|getty\s+images?|shutterstock)"
    r")\s*$",
    re.IGNORECASE,
)

_TAG_RE = re.compile(r"<[^>]+>")


def strip_boilerplate(text: str) -> str:
    """Remove scraping artifacts (UI labels, newsletter prompts, player controls)
    line by line from raw article text. Safe to call on both plain text and HTML."""
    if not text:
        return text
    lines = text.splitlines(keepends=True)
    result = []
    for line in lines:
        text_only = _TAG_RE.sub("", line).replace("\xa0", " ").strip()
        if not text_only or not _BOILERPLATE_RE.fullmatch(text_only):
            result.append(line)
    return "".join(result)
