import re
import unicodedata


def clean_text(raw: str) -> list[str]:
    """
    Limpia texto para comparación real de contenido.
    Elimina: HTML, acentos, puntuación, espacios extra.
    Retorna lista de palabras en minúsculas (>1 caracter).
    """
    if not raw:
        return []
    # 1. Quitar etiquetas HTML
    text = re.sub(r"<[^>]+>", " ", raw)
    # 2. Quitar entidades HTML (&nbsp; &amp; etc.)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    # 3. Quitar acentos y diacríticos
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # 4. Quitar todo lo que no sea letra o espacio
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    # 5. Lowercase, split y filtrar palabras cortas
    return [w for w in text.lower().split() if len(w) > 1]


def compare_texts(ai_text: str, saved_text: str) -> dict:
    """
    Compara el texto generado por la IA con el texto guardado por el redactor.
    Solo cuenta palabras reales — sin puntuación, espacios, acentos ni HTML.

    Retorna:
        words_from_ai   : palabras de la IA que sobrevivieron en el texto guardado
        words_added     : palabras nuevas que agregó el redactor
        words_removed   : palabras de la IA que el redactor eliminó
        pct_ai_kept     : porcentaje de palabras de la IA conservadas (0.0 a 1.0)
        acceptance_level: 'accepted' >= 0.70 | 'modified' 0.30-0.69 | 'rewrite' < 0.30
    """
    ai_words    = set(clean_text(ai_text))
    saved_words = set(clean_text(saved_text))

    if not ai_words:
        return {
            "words_from_ai":   0,
            "words_added":     len(saved_words),
            "words_removed":   0,
            "pct_ai_kept":     0.0,
            "acceptance_level": "manual",
        }

    words_from_ai = len(ai_words & saved_words)
    words_removed = len(ai_words - saved_words)
    words_added   = len(saved_words - ai_words)
    pct_ai_kept   = round(words_from_ai / len(ai_words), 4)

    if pct_ai_kept >= 0.70:
        level = "accepted"
    elif pct_ai_kept >= 0.30:
        level = "modified"
    else:
        level = "rewrite"

    return {
        "words_from_ai":   words_from_ai,
        "words_added":     words_added,
        "words_removed":   words_removed,
        "pct_ai_kept":     pct_ai_kept,
        "acceptance_level": level,
    }


def extract_clean_text_from_generation(processed_output: dict) -> str:
    """
    Extrae el texto principal de un processed_output de ai_generations.
    Prioriza el campo 'desc', luego junta todos los campos de texto disponibles.
    """
    if not processed_output:
        return ""

    fields = (
        processed_output
        .get("generatedContent", {})
        .get("processed_fields", {})
    )
    if not fields:
        fields = processed_output.get("processed_fields", {})

    if not fields:
        return ""

    # Campos de texto en orden de prioridad
    parts = []
    for key in sorted(fields.keys()):
        val = fields.get(key, "")
        if isinstance(val, str) and val and "No hay datos" not in val:
            parts.append(val)

    return " ".join(parts)
