# pipelines/summarization_pipeline.py
"""
Text summarisation pipeline using BART-large-CNN.
Takes a cluster of raw text reports and produces a concise incident summary.
"""

# Lazy-load to avoid heavy model download when not needed
_summarizer = None


def _get_summarizer():
    global _summarizer
    if _summarizer is None:
        try:
            from transformers import pipeline
            _summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
            )
        except Exception as e:
            print(f"⚠️ Summarisation model not available: {e}")
            _summarizer = "unavailable"
    return _summarizer


def summarize_texts(texts: list[str], max_length: int = 60, min_length: int = 15) -> str:
    """
    Summarise a list of text reports into a single concise incident description.

    Falls back to simple concatenation if the model is unavailable.
    """
    if not texts:
        return ""

    combined = " ".join(t.strip() for t in texts if t.strip())

    if len(combined.split()) < 10:
        return combined  # too short to summarise

    summarizer = _get_summarizer()

    if summarizer == "unavailable" or summarizer is None:
        # Fallback: first 100 chars
        return combined[:120] + ("..." if len(combined) > 120 else "")

    try:
        result = summarizer(
            combined,
            max_length=max_length,
            min_length=min_length,
            do_sample=False,
        )
        return result[0]["summary_text"]
    except Exception as e:
        print(f"⚠️ Summarisation failed: {e}")
        return combined[:120] + ("..." if len(combined) > 120 else "")
