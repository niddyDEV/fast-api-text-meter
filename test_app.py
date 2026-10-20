import pytest
from fastapi.testclient import TestClient

import app_final


@pytest.fixture
def client():
    with TestClient(app_final.app) as test_client:
        yield test_client

def test_index_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "TextMeter" in response.text
    assert 'id="analysis-form"' in response.text

def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version(client):
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"version": app_final.app.version}


def test_text_stats(client):
    response = client.post(
        "/text/stats",
        json={"text": "Привет, мир!"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "words": 2,
        "characters": 12,
        "characters_without_spaces": 11,
        "vowels": 3,
        "consonants": 6,
        "signs": 0,
    }


def test_text_stats_with_spaces(client):
    response = client.post(
        "/text/stats",
        json={"text": "Привет\nмир\t!"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "words": 2,
        "characters": 12,
        "characters_without_spaces": 10,
        "vowels": 3,
        "consonants": 6,
        "signs": 0,
    }


def test_reading_time(client, monkeypatch):
    monkeypatch.setattr(app_final, "READING_SPEED_WPM", 200)

    response = client.post(
        "/text/reading-time",
        json={
            "text": (
                "Один два три четыре пять "
                "шесть семь восемь девять десять"
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "words": 10,
        "reading_speed_wpm": 200,
        "estimated_seconds": 3.0,
    }


def test_reading_time_uses_configured_speed(client, monkeypatch):
    monkeypatch.setattr(app_final, "READING_SPEED_WPM", 100)

    response = client.post(
        "/text/reading-time",
        json={
            "text": (
                "Один два три четыре пять "
                "шесть семь восемь девять десять"
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "words": 10,
        "reading_speed_wpm": 100,
        "estimated_seconds": 6.0,
    }


def test_top_words(client):
    response = client.post(
        "/text/top-words",
        params={"limit": 2},
        json={"text": "Кот, кот! Пёс. Птица птица ПТИЦА."},
    )

    assert response.status_code == 200
    assert response.json() == {
        "top_words": [
            {"word": "птица", "count": 3},
            {"word": "кот", "count": 2},
        ]
    }


def test_top_words_alphabetical_order_on_tie(client):
    response = client.post(
        "/text/top-words",
        params={"limit": 5},
        json={"text": "Банан арбуз банан арбуз"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "top_words": [
            {"word": "арбуз", "count": 2},
            {"word": "банан", "count": 2},
        ]
    }


def test_top_words_default_limit(client):
    response = client.post(
        "/text/top-words",
        json={"text": "арбуз банан вишня груша дыня ежевика"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "top_words": [
            {"word": "арбуз", "count": 1},
            {"word": "банан", "count": 1},
            {"word": "вишня", "count": 1},
            {"word": "груша", "count": 1},
            {"word": "дыня", "count": 1},
        ]
    }


def test_top_words_without_words(client):
    response = client.post(
        "/text/top-words",
        json={"text": "!!!"},
    )

    assert response.status_code == 200
    assert response.json() == {"top_words": []}


@pytest.mark.parametrize(
    "endpoint",
    [
        "/text/stats",
        "/text/reading-time",
        "/text/top-words",
    ],
)
@pytest.mark.parametrize("text", ["", "   \n\t"])
def test_empty_text_rejected(client, endpoint, text):
    response = client.post(
        endpoint,
        json={"text": text},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, 21, "abc"])
def test_invalid_limit_rejected(client, limit):
    response = client.post(
        "/text/top-words",
        params={"limit": limit},
        json={"text": "Кот и пёс"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "endpoint",
    [
        "/text/stats",
        "/text/reading-time",
        "/text/top-words",
    ],
)
def test_missing_text_rejected(client, endpoint):
    response = client.post(
        endpoint,
        json={},
    )

    assert response.status_code == 422
    
@pytest.mark.parametrize(
    "text, vowels, consonants, signs",
    [
        ("Привет, мир!", 3, 6, 0),
        ("АЕЁИОУЫЭЮЯ", 10, 0, 0),
        ("Йй", 0, 2, 0),
        ("Съешь", 1, 2, 2),
        ("Python 123!", 0, 0, 0),
        ("!!!", 0, 0, 0),
    ],
)
def test_russian_letter_counts(
    client,
    text,
    vowels,
    consonants,
    signs,
):
    response = client.post(
        "/text/stats",
        json={"text": text},
    )

    assert response.status_code == 200

    result = response.json()

    assert result["vowels"] == vowels
    assert result["consonants"] == consonants
    assert result["signs"] == signs