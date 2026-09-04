"""Minimal REST API for local OCR with Tesseract and pytesseract."""

import io
import os
import shutil
import time
from collections import OrderedDict
from typing import Annotated

import pytesseract
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
from pytesseract import Output

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "40000000"))


class WordResult(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=100)
    left: int
    top: int
    width: int
    height: int


class OCRResponse(BaseModel):
    engine: str = "tesseract"
    filename: str
    language: str
    text: str
    confidence: float | None
    word_count: int
    duration_ms: int
    words: list[WordResult]


app = FastAPI(
    title="Tesseract OCR API",
    version="1.0.0",
    description="Offline image OCR using Tesseract through the pytesseract wrapper.",
)


def extract_image(
    image: Image.Image, language: str
) -> tuple[str, float | None, list[WordResult]]:
    data = pytesseract.image_to_data(
        image,
        lang=language,
        config="--oem 1 --psm 3",
        output_type=Output.DICT,
    )

    lines: OrderedDict[tuple[int, int, int], list[str]] = OrderedDict()
    words: list[WordResult] = []
    confidences: list[float] = []

    for index, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            continue
        if confidence < 0:
            continue

        line_key = (
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        lines.setdefault(line_key, []).append(text)
        confidences.append(confidence)
        words.append(
            WordResult(
                text=text,
                confidence=round(confidence, 2),
                left=int(data["left"][index]),
                top=int(data["top"][index]),
                width=int(data["width"][index]),
                height=int(data["height"][index]),
            )
        )

    full_text = "\n".join(" ".join(tokens) for tokens in lines.values())
    mean_confidence = (
        round(sum(confidences) / len(confidences), 2) if confidences else None
    )
    return full_text, mean_confidence, words


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "engine": "tesseract",
        "executable_available": bool(shutil.which("tesseract")),
    }


@app.post("/extract", response_model=OCRResponse)
async def extract(
    file: Annotated[UploadFile, File()],
    language: Annotated[str, Query(min_length=3, max_length=32)] = "eng",
) -> OCRResponse:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The uploaded file is too large.")

    started = time.perf_counter()
    try:
        with Image.open(io.BytesIO(content)) as source:
            width, height = source.size
            if width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413, detail="The image dimensions are too large."
                )
            image = ImageOps.exif_transpose(source).convert("RGB")
        text, confidence, words = extract_image(image, language)
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=415, detail="Upload a PNG, JPEG, TIFF, or BMP image."
        ) from exc
    except pytesseract.TesseractNotFoundError as exc:
        raise HTTPException(
            status_code=503, detail="Tesseract is not installed."
        ) from exc
    except pytesseract.TesseractError as exc:
        raise HTTPException(status_code=422, detail=f"Tesseract failed: {exc}") from exc

    return OCRResponse(
        filename=file.filename or "image",
        language=language,
        text=text,
        confidence=confidence,
        word_count=len(words),
        duration_ms=round((time.perf_counter() - started) * 1000),
        words=words,
    )
