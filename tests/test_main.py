import io
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from main import app

client = TestClient(app)


def image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (100, 40), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["engine"] == "tesseract"


@patch("main.pytesseract.image_to_data")
def test_extract(mock_image_to_data) -> None:
    mock_image_to_data.return_value = {
        "text": ["Hello", "OCR"],
        "conf": ["95", "85"],
        "block_num": [1, 1],
        "par_num": [1, 1],
        "line_num": [1, 1],
        "left": [10, 50],
        "top": [10, 10],
        "width": [30, 25],
        "height": [15, 15],
    }

    response = client.post(
        "/extract?language=eng",
        files={"file": ("sample.png", image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["text"] == "Hello OCR"
    assert result["confidence"] == 90.0
    assert result["word_count"] == 2


def test_rejects_non_image() -> None:
    response = client.post(
        "/extract",
        files={"file": ("sample.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 415
