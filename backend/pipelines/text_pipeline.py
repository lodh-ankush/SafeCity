from transformers import pipeline
from core.utils import get_timestamp
from core.db import log_event

# Hugging Face text classification pipeline
classifier = pipeline(
    "text-classification",
    model="bhadresh-savani/bert-base-uncased-emotion",
)


def process_text(text_path="data/text/sample_reports.txt"):
    with open(text_path, "r") as f:
        text_data = f.readlines()

    results = []
    for line in text_data:
        line = line.strip()
        if not line:
            continue
        res = classifier(line)[0]
        log_event(get_timestamp(), "text", res["label"], res["score"])
        results.append({"text": line, "label": res["label"], "score": res["score"]})
    return results


if __name__ == "__main__":
    print(process_text())
