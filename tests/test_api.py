import pandas as pd
import pytest

import main
from src import MovieStorage


def test_movies_persist(client, test_storage, uploaded_movies):
    # A second storage object on the same database file
    reopened = MovieStorage(test_storage.db_path)
    df = reopened.get()

    assert len(df) == 20
    assert reopened.count_movies() == 20
    assert list(df.columns) == ["title", "release_year", "rating", "genre"]

    original = pd.read_csv("fixtures/sample_movies.csv")
    assert df["title"].tolist() == original["title"].tolist()

    db_ids = [row["id"] for row in reopened.select_columns(["title"], limit=100)]
    response = client.get("/movies", params={"limit": 100})
    api_ids = [movie["id"] for movie in response.json()["data"]]
    assert db_ids == api_ids == list(range(1, 21))


def test_cache_and_processing(client, uploaded_movies, processing_body):
    # TODO 1: both limits are cached and match their responses
    first = {}
    for limit in (100, 1):
        response = client.get("/movies", params={"limit": limit})
        assert response.status_code == 200
        assert main.cache.get(limit) == response.json()
        first[limit] = response.json()

    # TODO 2: repeating limit=100 returns the same response
    repeat = client.get("/movies", params={"limit": 100})
    assert repeat.status_code == 200
    assert repeat.json() == first[100]

    # TODO 3: processing clears both cache entries
    processed = client.post("/movies/process", json=processing_body)
    assert processed.status_code == 200
    body = processed.json()
    assert body["validation_rows_removed"] == 0
    assert body["cleaning_report"]["rows_before"] == 20
    assert body["cleaning_report"]["rows_after"] == 16
    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    # TODO 4: fresh retrieval shows 16 rows and is cached again
    after = client.get("/movies", params={"limit": 100})
    assert after.status_code == 200
    data = after.json()
    assert data["total_rows"] == 16
    assert [m["title"] for m in data["data"]] == [f"Movie {c}" for c in "ABCDEFGHIJKLMNOP"]
    assert [m["id"] for m in data["data"]] == list(range(1, 17))
    assert main.cache.get(100) == data


def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    # TODO 1: populate the cache
    first = client.get("/movies", params={"limit": 100})
    assert first.status_code == 200

    # TODO 2: make any database read fail the test
    def fail(*args, **kwargs):
        pytest.fail("Database was accessed on a cache hit")

    monkeypatch.setattr(main.storage, "select_columns", fail)
    monkeypatch.setattr(main.storage, "count_movies", fail)

    # TODO 3: the repeat is served from the cache
    second = client.get("/movies", params={"limit": 100})
    assert second.status_code == 200
    assert second.json() == first.json()