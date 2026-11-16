import re
import unicodedata

_HF = re.compile(r"\(?\b[hf]\s*/\s*[hf]\b\)?")
_ESPACES = re.compile(r"\s+")


def normaliser_texte(s: str | None) -> str:
    """Minuscules, sans accents, sans « h/f », espaces simples."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s.lower().replace("’", "'"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _ESPACES.sub(" ", _HF.sub(" ", s)).strip()
