from transformers import pipeline
from core.utils import get_timestamp
from core.db import log_event

# MIT finetuned AST model for audio classification
classifier = pipeline(
    "audio-classification",
    model="MIT/ast-finetuned-audioset-10-10-0.4593",
)


def process_audio(audio_path="data/audio/siren.wav"):
    results = classifier(audio_path)
    best_result = max(results, key=lambda x: x["score"])

    # Log result
    log_event(get_timestamp(), "audio", best_result["label"], best_result["score"])
    return best_result


if __name__ == "__main__":
    print(process_audio())
