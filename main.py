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

from runwayml import AsyncRunwayML
import base64

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


@app.post("/generate-ai")
async def generate_ai_video(image: UploadFile = File(...)):
    RUNWAY_API_KEY = os.getenv("RUNWAYML_API_SECRET")
    if not RUNWAY_API_KEY:
        return {"error": "Missing RunwayML API key."}

    contents = await image.read()
    encoded_image = base64.b64encode(contents).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{encoded_image}"

    client = AsyncRunwayML(api_key=RUNWAY_API_KEY)

    try:
        task = await client.image_to_video.create(
            model="gen4_turbo",
            prompt_image=data_uri,
            prompt_text="Smooth cinematic motion",
            ratio="1280:720",
            duration=5
        )
    except Exception as e:
        return {"error": f"Failed to create Runway task: {str(e)}"}

    task_id = task.id

    # Poll for completion
    for _ in range(20):
        await asyncio.sleep(10)
        status = await client.tasks.retrieve(task_id)
        if status.status == "SUCCEEDED":
            video_url = status.output.video
            break
        elif status.status == "FAILED":
            return {"error": "RunwayML generation failed."}
    else:
        return {"error": "RunwayML generation timed out."}

    # Download the video file
    async with httpx.AsyncClient() as http_client:
        video_resp = await http_client.get(video_url)

    temp_file = NamedTemporaryFile(delete=False, suffix=".mp4")
    temp_file.write(video_resp.content)
    temp_file.close()

    return FileResponse(temp_file.name, media_type="video/mp4", filename="ai_video.mp4")