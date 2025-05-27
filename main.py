from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List
from io import BytesIO
import imageio

app = FastAPI()

# ✅ Replace with the current Netlify frontend
origins = [
    "https://aesthetic-stardust-a59f41.netlify.app",
    "https://remarkable-ganache-5b3ba1.netlify.app",
    "https://683501edc3c24ac406437f20--aesthetic-stardust-a59f41.netlify.app",  # ← Permalink
    "http://localhost:3000"  # Optional: local dev
]

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root check route
@app.get("/")
def read_root():
    return {"status": "Backend working"}

# ✅ Main video generation endpoint
@app.post("/generate")
async def generate_video(files: List[UploadFile] = File(...)):
    images = []
    for file in files:
        contents = await file.read()
        image = imageio.v2.imread(contents)
        images.append(image)

    video_bytes = BytesIO()
    writer = imageio.get_writer(video_bytes, format="mp4", fps=1)
    for img in images:
        writer.append_data(img)
    writer.close()
    video_bytes.seek(0)

    return StreamingResponse(video_bytes, media_type="video/mp4")