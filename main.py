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
    writer = imageio.get_writer(video_bytes, format="mp4", fps=1)
    for frame in frames:
        try:
            resized = np.array(Image.fromarray(frame).resize((1280, 720)))  # Resize to HD resolution
            writer.append_data(resized)
        except Exception as e:
            print(f"Error processing frame: {e}")
    writer.close()
    video_bytes.seek(0)

    return StreamingResponse(video_bytes, media_type="video/mp4")