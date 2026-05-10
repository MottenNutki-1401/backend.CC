from fastapi import APIRouter, UploadFile, File, HTTPException
from services.text_extractor import extract_text
import os

router = APIRouter()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):

    saved_files = []
    texts = []

    for file in files:

        extension = os.path.splitext(file.filename)[1].lower()

        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"{file.filename} is not supported"
            )

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        text = extract_text(file_path)

        print(f"\n--- {file.filename} ---")
        print(text[:200])

        texts.append(text)  # raw txt only
        saved_files.append(file.filename)

    return {
        "message": "Files uploaded successfully",
        "files": saved_files,
        "texts": texts
    }