from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from transformers import DetrImageProcessor, DetrForObjectDetection
import torch
from PIL import Image
import requests
import io
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

app = FastAPI(title="DETR Object Detection API")

device = "cuda" if torch.cuda.is_available() else "cpu"

processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50")
model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50")

model.to(device)
model.eval()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/info")
def info():
    return {
        "model": "facebook/detr-resnet-50",
        "task": "object detection",
        "framework": "HuggingFace Transformers + FastAPI"
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    inputs = processor(images=image, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model(**inputs)

    target_sizes = torch.tensor(
        [image.size[::-1]]).to(device)
    results = processor.post_process_object_detection(
        outputs, target_sizes=target_sizes, threshold=0.5)[0]

    detections = []
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        detections.append({
            "score": float(score),
            "label": model.config.id2label[int(label)],
            "box": [float(x) for x in box]
        })

    return JSONResponse(content={"detections": detections})
