import logging
import os

from pathlib import Path
from google.cloud import bigquery
from dotenv import load_dotenv


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent


# Load .env
load_dotenv(BASE_DIR / ".env")


# GCP
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS"
)


# YouTube
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


# BigQuery datasets
RAW_DATASET = "youtube_raw"
CLEAN_DATASET = "youtube_clean"

# Schema
VIDEOS_SCHEMA = [
    bigquery.SchemaField("artist_name", "STRING"),
    bigquery.SchemaField("channel_id", "STRING"),
    bigquery.SchemaField("channel_title", "STRING"),
    bigquery.SchemaField("video_id", "STRING"),
    bigquery.SchemaField("video_title", "STRING"),
    bigquery.SchemaField("description", "STRING"),
    bigquery.SchemaField("published_at", "TIMESTAMP"),
    bigquery.SchemaField("duration", "STRING"),
    bigquery.SchemaField(
        "tags",
        "STRING",
        mode="REPEATED"
    ),
    bigquery.SchemaField("category_id", "STRING"),
    bigquery.SchemaField("view_count", "INT64"),
    bigquery.SchemaField("like_count", "INT64"),
    bigquery.SchemaField("comment_count", "INT64"),

    bigquery.SchemaField("batch_id", "STRING"),
    bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    bigquery.SchemaField("source", "STRING"),
    bigquery.SchemaField("ingestion_date", "DATE"),
]


COMMENTS_SCHEMA = [
    bigquery.SchemaField("artist_name", "STRING"),
    bigquery.SchemaField("channel_id", "STRING"),
    bigquery.SchemaField("video_id", "STRING"),
    bigquery.SchemaField("comment_id", "STRING"),
    bigquery.SchemaField("parent_id", "STRING"),
    bigquery.SchemaField("author_name", "STRING"),
    bigquery.SchemaField("comment_text", "STRING"),
    bigquery.SchemaField("published_at", "TIMESTAMP"),
    bigquery.SchemaField("updated_at", "TIMESTAMP"),
    bigquery.SchemaField("like_count", "INT64"),
    bigquery.SchemaField("reply_count", "INT64"),

    bigquery.SchemaField("batch_id", "STRING"),
    bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    bigquery.SchemaField("source", "STRING"),
    bigquery.SchemaField("ingestion_date", "DATE"),
]

# Logging
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "pipeline.log"


LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    print(BASE_DIR)