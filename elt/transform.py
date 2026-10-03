import config
import logging

from google.cloud import bigquery

logger = logging.getLogger(__name__)

def get_bigquery_client():
    return bigquery.Client(
        project=config.GCP_PROJECT_ID
    )

def transform_videos(raw_table_id, clean_table_id):

    query = f"""
    CREATE OR REPLACE TABLE `{clean_table_id}` AS

    SELECT
        artist_name,
        channel_id,
        channel_title,
        video_id,
        TRIM(video_title) AS video_title,
        description,
        published_at,
        duration,
        tags,
        category_id,
        COALESCE(view_count, 0) AS view_count,
        COALESCE(like_count, 0) AS like_count,
        COALESCE(comment_count, 0) AS comment_count,
        batch_id,
        extracted_at,
        source,
        ingestion_date

    FROM `{raw_table_id}`

    WHERE video_id IS NOT NULL
    """

    client = get_bigquery_client()

    job = client.query(query)
    job.result()

    logger.info(f"Videos transformed: {raw_table_id} -> {clean_table_id}")

def transform_comments(raw_table_id, clean_table_id):

    query = f"""
    CREATE OR REPLACE TABLE `{clean_table_id}` AS

    SELECT
        artist_name,
        channel_id,
        video_id,
        comment_id,
        parent_id,
        author_name,
        TRIM(comment_text) AS comment_text,
        published_at,
        updated_at,
        COALESCE(like_count, 0) AS like_count,
        COALESCE(reply_count, 0) AS reply_count,
        batch_id,
        extracted_at,
        source,
        ingestion_date

    FROM `{raw_table_id}`

    WHERE comment_id IS NOT NULL
    """

    client = get_bigquery_client()

    job = client.query(query)
    job.result()

    logger.info(f"Comments transformed: {raw_table_id} -> {clean_table_id}")


def transform(batch_id):

    raw_videos_table = (
        f"{config.GCP_PROJECT_ID}."
        f"{config.RAW_DATASET}."
        f"videos_{batch_id}"
    )

    raw_comments_table = (
        f"{config.GCP_PROJECT_ID}."
        f"{config.RAW_DATASET}."
        f"comments_{batch_id}"
    )


    clean_videos_table = (
        f"{config.GCP_PROJECT_ID}."
        f"{config.CLEAN_DATASET}."
        f"videos_{batch_id}"
    )

    clean_comments_table = (
        f"{config.GCP_PROJECT_ID}."
        f"{config.CLEAN_DATASET}."
        f"comments_{batch_id}"
    )

    logger.info(f"Transform Batch: {batch_id}")

    transform_videos(
        raw_videos_table,
        clean_videos_table
    )

    transform_comments(
        raw_comments_table,
        clean_comments_table
    )

    logger.info("Transform Finished")

