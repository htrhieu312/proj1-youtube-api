import pandas as pd
from . import config
import logging

from datetime import date, datetime, timezone
from google.cloud import bigquery

logger = logging.getLogger(__name__)


def get_bigquery_client():
    return bigquery.Client(
        project=config.GCP_PROJECT_ID
    )

def add_metadata(df: pd.DataFrame, batch_id: str) -> pd.DataFrame:
    df = df.copy()

    now = datetime.now(timezone.utc)

    df["batch_id"] = batch_id
    df["extracted_at"] = now
    df["source"] = "youtube_api"
    df["ingestion_date"] = now.date()

    if "published_at" in df.columns:
        df["published_at"] = pd.to_datetime(
            df["published_at"],
            utc=True
        )

    if "updated_at" in df.columns:
        df["updated_at"] = pd.to_datetime(
            df["updated_at"],
            utc=True
        )

    return df

def load_to_bigquery(df: pd.DataFrame,  table_id: str, schema: list, write_disposition: str):
    
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=write_disposition,
    )

    client = get_bigquery_client()

    job = client.load_table_from_dataframe(
        df,
        table_id,
        job_config=job_config,
    )

    job.result() 

    logger.info(f"Loaded {len(df)} rows into {table_id}.")


def load_videos(videos_df : pd.DataFrame, table_id : str, schema : list, write_disposition : str):
    load_to_bigquery(
        df=videos_df,
        table_id=table_id,
        schema=schema,
        write_disposition=write_disposition
    )


def load_comments(comments_df : pd.DataFrame, table_id : str, schema : list, write_disposition : str):
    load_to_bigquery(
        df=comments_df,
        table_id=table_id,
        schema=schema,
        write_disposition=write_disposition
    )


def load(extracted_data, batch_id):
    # batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    videos_table_id = f"{config.GCP_PROJECT_ID}.{config.RAW_DATASET}.videos_{batch_id}"
    comment_table_id = f"{config.GCP_PROJECT_ID}.{config.RAW_DATASET}.comments_{batch_id}"

    first_artist = True

    for artist in extracted_data:

        artist_name = artist["artist_name"]
        videos_df = artist["videos"]
        comments_df = artist["comments"]

        logger.info(f"Loading data for artist: {artist_name}")

        videos_df = add_metadata(videos_df, batch_id)
        comments_df = add_metadata(comments_df, batch_id)

        if first_artist:
            write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
            
        else:
            write_disposition = bigquery.WriteDisposition.WRITE_APPEND

        load_videos(
            videos_df=videos_df,
            table_id=videos_table_id,
            schema=config.VIDEOS_SCHEMA,
            write_disposition=write_disposition
        )

        load_comments(
            comments_df=comments_df,
            table_id=comment_table_id,
            schema=config.COMMENTS_SCHEMA,
            write_disposition=write_disposition
        )

        first_artist = False

    logger.info("Data loading completed for all artists.")
