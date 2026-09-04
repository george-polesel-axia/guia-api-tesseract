# Tesseract OCR API

[![CI](https://github.com/george-polesel-axia/guia-api-tesseract/actions/workflows/ci.yml/badge.svg)](https://github.com/george-polesel-axia/guia-api-tesseract/actions/workflows/ci.yml)

A small, production-minded REST API for extracting text from images with
[Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/) and the `pytesseract`
Python wrapper.

This repository reconstructs one of the OCR components used in the former
ProWatsom document-ingestion backend. It contains no customer documents,
credentials, or proprietary business rules.

## What it demonstrates

- Offline OCR with no per-request cloud cost.
- PNG, JPEG, TIFF, and BMP processing.
- Portuguese and English language models.
- Word-level confidence scores and bounding boxes.
- Bounded uploads and image-dimension validation.
- FastAPI, Docker, automated tests, and GitHub Actions.

## Run with Docker

```bash
docker build -t tesseract-ocr-api .
docker run --rm -p 8000:8000 tesseract-ocr-api
```

Open `http://localhost:8000/docs`.

## Run locally

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-por
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload
```

## Extract text

```bash
curl -X POST "http://localhost:8000/extract?language=por%2Beng" \
  -F "file=@sample.png"
```

Example response:

```json
{
  "engine": "tesseract",
  "filename": "sample.png",
  "language": "por+eng",
  "text": "Recognized text",
  "confidence": 93.42,
  "word_count": 2,
  "duration_ms": 318,
  "words": [
    {
      "text": "Recognized",
      "confidence": 94.1,
      "left": 20,
      "top": 30,
      "width": 110,
      "height": 24
    }
  ]
}
```

## Limits

Tesseract works best with clear printed text. Image preprocessing, page
segmentation mode, resolution, font size, rotation, and scan quality can all
affect accuracy. PDFs are intentionally outside this repository; use the
separate `pdftotext` example for digital PDFs or rasterize scanned PDF pages
before OCR.

## Tests

```bash
pytest -q
```

## License

MIT © 2026 George Hamilton Buzzi Polesel.
