import cv2
from transformers import pipeline
from core.utils import get_timestamp
from core.db import log_event

# using kinetics 400 model for video classification
classifier = pipeline(
    "video-classification",
    model="MCG-NJU/videomae-base-finetuned-kinetics",
)


def process_video(video_path="data/sample_videos/traffic.mp4"):
    print("🚦 Processing video...")

    results = classifier(video_path)

    if not results:
        print("⚠️ No results returned from the model. Please check your video or model config.")
        return {"label": "unknown", "score": 0.0}

    best_result = max(results, key=lambda x: x["score"])
    print(f"✅ Best prediction: {best_result['label']} ({best_result['score']:.2f})")
    return best_result


if __name__ == "__main__":
    print(process_video())
