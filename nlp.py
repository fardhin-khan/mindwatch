import os
import re


NEGATORS = {
    "not", "no", "never", "dont", "don't", "do not", "cannot", "can't",
    "cant", "isn't", "isnt", "arent", "aren't", "wasn't", "wasnt",
    "without", "barely", "hardly", "nor", "none"
}

INTENSIFIERS = {
    "very", "really", "so", "extremely", "totally", "absolutely",
    "quite", "super", "highly", "deeply", "terribly", "incredibly"
}

NEGATIVE = {
    "sad", "sadness", "depressed", "depression", "depressing", "stress",
    "stressed", "stressful", "anxious", "anxiety", "tired", "lonely",
    "loneliness", "hopeless", "helpless", "worried", "worry", "fear",
    "afraid", "scared", "angry", "anger", "upset", "cry", "crying",
    "exhausted", "overwhelmed", "difficult", "difficulty", "worthless",
    "empty", "numb", "panic", "dread", "low", "hurt", "pain", "painful"
}

POSITIVE = {
    "happy", "happiness", "good", "great", "calm", "relaxed", "healthy",
    "better", "best", "positive", "hopeful", "hope", "energetic",
    "peaceful", "confident", "grateful", "joy", "joyful", "content",
    "fine", "okay", "ok", "love", "loved", "safe", "strong", "rested"
}

CRISIS = {
    "suicide", "suicidal", "kill myself", "killing myself", "end my life",
    "end my own life", "self harm", "self-harm", "harm myself",
    "take my life", "don't want to live", "want to die", "better off dead"
}

# Generic stop-words removed during preprocessing. Negators and
# intensifiers are deliberately kept so the lexicon scorer can still
# see negation/emphasis context around each keyword.
GENERIC_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "while",
    "am", "are", "was", "were", "be", "been", "being", "is", "do", "does",
    "did", "doing", "has", "have", "had", "having", "i", "me", "my", "mine",
    "you", "your", "yours", "he", "him", "his", "she", "her", "hers", "it",
    "its", "we", "us", "our", "they", "them", "their", "this", "that",
    "these", "those", "at", "by", "for", "with", "about", "between", "into",
    "through", "of", "to", "from", "in", "on", "as", "so", "such", "than",
    "then", "too", "can", "will", "just", "should", "would", "could", "now",
    "what", "which", "who", "whom", "when", "where", "why", "how", "all",
    "any", "both", "each", "few", "more", "most", "other", "some", "only",
    "own", "same", "again", "also", "off", "over", "under", "while", "upon"
}

# Simple suffix normaliser so "stressing" -> "stress", "crying" -> "cry",
# "feeling" -> "feel". Only applied when the shorter form exists in the
# lexicon (checked in _lookup), so misspellings are never punished.
_SUFFIXES = (("ing", 3), ("ed", 2), ("es", 2), ("s", 1))


def _normalize(word):
    for suffix, cut in _SUFFIXES:
        if len(word) > 4 and word.endswith(suffix):
            return word[:-cut]
    return word


def preprocess_text(text):
    """Preprocessing pipeline: clean -> lowercase -> tokenize ->
    stop-word removal.

    Negators and intensifiers are always kept so the analysis layer
    can still detect negation and emphasis. Normalisation happens
    inside _lookup only when a dictionary form is found.
    """

    if not text:
        return []

    # Cleaning: replace smart quotes / dashes with spaces
    cleaned = re.sub(r"[\u2018\u2019\u201C\u201D'\"-]", " ", text)

    # Lowercase + tokenization
    tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", cleaned.lower())

    # Stop-word removal (negators + intensifiers always kept)
    return [
        token for token in tokens
        if token not in GENERIC_STOP_WORDS
        or token in NEGATORS
        or token in INTENSIFIERS
    ]


def _lookup(word):
    """Lexicon hit for a word, with a light normalisation fallback."""

    if word in NEGATIVE or word in POSITIVE:
        return word
    base = _normalize(word)
    if base != word and (base in NEGATIVE or base in POSITIVE):
        return base
    return None


def _lexicon_score(tokens):
    """Negation- and intensifier-aware local scoring."""

    neg_score = 0.0
    pos_score = 0.0

    for i, word in enumerate(tokens):

        multiplier = 1.0
        if (i > 0 and tokens[i - 1] in INTENSIFIERS) or \
           (i > 1 and tokens[i - 2] in INTENSIFIERS):
            multiplier = 1.5

        negated = (
            (i > 0 and tokens[i - 1] in NEGATORS) or
            (i > 1 and tokens[i - 2] in NEGATORS)
        )

        hit = _lookup(word)

        if hit in NEGATIVE:
            if negated:
                pos_score += 0.5
            else:
                neg_score += 1.0 * multiplier

        elif hit in POSITIVE:
            if negated:
                neg_score += 0.5
            else:
                pos_score += 1.0 * multiplier

    return neg_score, pos_score


def analyze_text(text):
    """Local, privacy-friendly text analysis (no external calls).

    Returns a sentiment label, an educational 0-100 text risk score,
    and a word count. Optionally uses an LLM when API credentials are
    configured (see analyze_text_with_llm).
    """

    if not text or not text.strip():
        return {
            "sentiment": "Neutral",
            "text_risk": 0,
            "word_count": 0
        }

    lower = text.lower()
    raw_tokens = re.findall(r"\b[\w'']+\b", lower)
    raw_words = len(raw_tokens)

    # Preprocessing layer: clean -> lowercase -> tokenize -> stop-word
    # removal -> normalise (negators/intensifiers preserved).
    tokens = preprocess_text(text)

    # Feature counters
    unique_words = len(set(tokens))
    avg_word_len = round(
        (sum(len(w) for w in tokens) / len(tokens)) if tokens else 0,
        1
    )
    stop_words_removed = max(0, len(raw_tokens) - len(tokens))

    # Crisis language always maps to maximum risk.
    crisis = any(phrase in lower for phrase in CRISIS)

    neg_score, pos_score = _lexicon_score(tokens)

    if pos_score > neg_score:
        sentiment = "Positive"
    elif neg_score > pos_score:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    text_risk = int(neg_score * 12)
    if neg_score >= 4:
        text_risk += 15
    if neg_score >= 7:
        text_risk += 20
    if crisis:
        text_risk = 100

    text_risk = min(100, text_risk)

    return {
        "sentiment": sentiment,
        "text_risk": text_risk,
        "word_count": raw_words,
        "text_features": {
            "unique_words": unique_words,
            "avg_word_length": avg_word_len,
            "stop_words_removed": stop_words_removed
        }
    }


def analyze_text_with_llm(text):
    """Optional LLM-based analysis.

    Activated only when MINDWATCH_LLM_API_KEY and MINDWATCH_LLM_URL are
    set in the environment. Falls back to the local analyzer on any
    error so the app never breaks.
    """

    api_key = os.environ.get("MINDWATCH_LLM_API_KEY")
    api_url = os.environ.get("MINDWATCH_LLM_URL")

    if not api_key or not api_url:
        return analyze_text(text)

    try:
        import requests

        prompt = (
            "You are a mental-health triage assistant. "
            "Given the user text, reply ONLY with JSON: "
            '{"sentiment": "Positive|Neutral|Negative", '
            '"text_risk": 0-100, "word_count": integer}. '
            "Text: " + text
        )

        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": os.environ.get(
                    "MINDWATCH_LLM_MODEL", "gpt-3.5-turbo"
                ),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0
            },
            timeout=10
        )

        content = response.json()["choices"][0]["message"]["content"]
        data = __import__("json").loads(content)
        data["word_count"] = len(re.findall(r"\b\w+\b", text.lower()))
        return data

    except Exception:
        return analyze_text(text)
