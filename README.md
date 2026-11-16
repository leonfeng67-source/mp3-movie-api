# MP3 Movie API

This project is a FastAPI service that stores one movie collection in a SQLite database and lets clients retrieve, search, and clean it. `main.py` defines the endpoints, while `src/database.py` creates connections and the `movies` table, and `src/storage.py` runs all SQL for saving, counting, selecting, and filtering movies. `src/models.py` holds the Pydantic response models, `src/middleware.py` logs each request, and `data_pipeline/` provides the validation and processing functions from MP1. When a CSV is uploaded, the API checks its columns and rows, replaces the entire collection in one SQL transaction, and clears the cache. `GET /movies` first looks for a cached response in `src/cache.py`, a FakeRedis cache that keeps each result for 90 seconds, and only queries SQLite on a miss. `POST /movies/process` reads the stored movies, validates and cleans them with the MP1 functions, saves the result back to SQLite, and clears the cache so the next retrieval shows the updated data. Because the data lives in `data/movies.db`, it survives server restarts, while the cache is in memory and starts empty each time.

## Run the API

```
python -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs to try the endpoints.

## Run the tests

```
python -m pytest tests -v
```

## Sample processing request

After uploading `fixtures/sample_movies.csv`, send this to `POST /movies/process`:

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {"enabled": true, "axis": "rows"},
    "outliers": {
      "enabled": true,
      "columns": ["rating"],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

Expected result for the 20-row sample:

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
```