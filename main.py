import os
import httpx
import time
import asyncio
from fastapi.responses import FileResponse
from tempfile import NamedTemporaryFile
from dotenv import load_dotenv

load_dotenv()

RUNWAY_API_KEY = os.getenv("key_9ba1adaf008a8f412312660579987a902e4e5ff347a2f3b32d4acd28d739480b4633abdf88588c28acb66a762e8bc14b9f09c4fa0fdefa59a5cee0946252963e")
RUNWAY_MODEL_ID = "runwayml/gen-4-turbo"
RUNWAY_API_URL = f"https://api.runwayml.com/v1/inference/{RUNWAY_MODEL_ID}"
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List
from io import BytesIO
import imageio
from PIL import Image
import numpy as np

app = FastAPI()

origins = [
    "https://aesthetic-stardust-a59f41.netlify.app",
    "https://683501edc3c24ac406437f20--aesthetic-stardust-a59f41.netlify.app",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Backend working"}

@app.post("/generate")
async def generate_video(images: List[UploadFile] = File(...)):
    frames = []
    for file in images:
        contents = await file.read()
        try:
            image = imageio.v2.imread(contents)
            if image is not None:
                frames.append(image)
            else:
                print(f"Skipped unreadable file: {file.filename}")
        except Exception as e:
            print(f"Error reading {file.filename}: {e}")
            continue

    if not frames:
        return {"error": "No valid images provided."}

    video_bytes = BytesIO()
    writer = imageio.get_writer(
        video_bytes,
        format="mp4",
        fps=1,
        macro_block_size=None  # allow custom resolution
    )
    max_width, max_height = 1280, 720
    for frame in frames:
        try:
            pil_img = Image.fromarray(frame)
            if pil_img.width > max_width or pil_img.height > max_height:
                pil_img.thumbnail((max_width, max_height))
            resized = np.array(pil_img)
            writer.append_data(resized)
        except Exception as e:
            print(f"Error processing frame: {e}")
    writer.close()
    video_bytes.seek(0)

    return StreamingResponse(video_bytes, media_type="video/mp4")


# New AI video generation endpoint using RunwayML Gen-4 Turbo
@app.post("/generate-ai")
async def generate_ai_video(image: UploadFile = File(...)):
    if not RUNWAY_API_KEY:
        return {"error": "Runway API key not configured."}

    contents = await image.read()
    temp_image = NamedTemporaryFile(delete=False, suffix=".jpg")
    temp_image.write(contents)
    temp_image.close()

    headers = {
        "Authorization": f"Bearer {RUNWAY_API_KEY}",
        "Content-Type": "application/json"
    }

    files = {
        "image": open(temp_image.name, "rb")
    }

    json_payload = {
        "prompt": "smooth cinematic movement",
        "seed": 42,
        "output_format": "mp4"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RUNWAY_API_URL,
            headers=headers,
            files={"input_image": files["image"]},
            json=json_payload
        )

    os.remove(temp_image.name)

    if response.status_code != 200:
        return {"error": "Failed to send image to Runway."}

    task = response.json()
    task_id = task.get("id")

    # Poll for completion
    result_url = None
    for _ in range(20):
        await asyncio.sleep(3)
        async with httpx.AsyncClient() as client:
            poll = await client.get(f"{RUNWAY_API_URL}/{task_id}", headers=headers)
        status = poll.json()
        if status.get("status") == "succeeded":
            result_url = status["output"].get("video")
            break
        elif status.get("status") == "failed":
            return {"error": "Video generation failed."}

    if not result_url:
        return {"error": "Timed out waiting for video."}

    # Download and return video
    async with httpx.AsyncClient() as client:
        video_resp = await client.get(result_url)

    video_temp = NamedTemporaryFile(delete=False, suffix=".mp4")
    video_temp.write(video_resp.content)
    video_temp.close()

    return FileResponse(video_temp.name, media_type="video/mp4", filename="ai_video.mp4")