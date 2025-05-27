from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List
from io import BytesIO
import imageio

app = FastAPI()

origins = [
    "https://aesthetic-stardust-a59f41.netlify.app",
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
async def generate_video(images: List[UploadFile] = File(...)):  # <-- match the field name
    frames = []
    for file in images:
        contents = await file.read()
        image = imageio.v2.imread(contents)
        frames.append(image)

    video_bytes = BytesIO()
    writer = imageio.get_writer(video_bytes, format="mp4", fps=1)
    for frame in frames:
        writer.append_data(frame)
    writer.close()
    video_bytes.seek(0)

    return StreamingResponse(video_bytes, media_type="video/mp4")