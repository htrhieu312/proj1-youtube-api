import json
import logging
import requests
import time
import pandas as pd 
from . import config

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

VIDEO_BATCH_SIZE = 50
PLAYLIST_PAGE_SIZE = 50
COMMENT_PAGE_SIZE = 100
TOP_VIDEO_LIMIT = 10
MAX_COMMENT_PAGES = 3
MAX_RETRIES = 3
RETRY_BASES_SECONDS = 2


youtube = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
logger = logging.getLogger(__name__)


def execute_with_retry(request, description):

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            return request.execute()

        except HttpError as e:

            status_code = e.resp.status

            if status_code in (400, 401, 403, 404):
                logger.error("%s failed with Http %s: %s", description, status_code, e)
                raise

            logger.warning("%s failed (attempt %d/%d), Http: %s", description, attempt, MAX_RETRIES, status_code)

        except Exception as e:
            logger.warning("%s failed (attempt %d/%d): %s", description, attempt, MAX_RETRIES, e)

        if attempt < MAX_RETRIES:

            sleep_seconds = RETRY_BASES_SECONDS ** attempt

            logger.info("Retrying in %d seconds...", sleep_seconds)

            time.sleep(sleep_seconds)


    raise RuntimeError(f"{description} failed after {MAX_RETRIES} attempts")    


def load_artists():

    artist_file = config.BASE_DIR / "data" / "artists.csv"

    logger.info("Loading artists from %s", artist_file)

    if not artist_file.exists() :
        raise FileExistsError(f"Not found {artist_file}")

    df = pd.read_csv(artist_file)

    required_columns = {"artist_name", "channel_id"}

    missing_columns = required_columns - set(df.columns)

    if missing_columns: 
        raise ValueError("Missing required columns: ", + ", ".join(sorted(missing_columns)))

    df = df.dropna(subset =["artist_name", "channel_id"])

    df = df.drop_duplicates(subset = ["artist_name"])

    logger.info("Loaded %d artists", len(df))

    return df


def get_uploads_playlist_id(channel_id):

    logger.debug("Getting uploads playlists channel %s", channel_id)

    request = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    )

    response = execute_with_retry(request, f"Get channel {channel_id}")


    items = response.get("items", [])

    if not items:
        logger.warning("Channel not found: %s", channel_id)

        return None

    uploads_playlist_id = (
        items[0]
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )

    if not uploads_playlist_id:

        logger.warning("Uploads playlist not found for channel: %s", channel_id)
 
        return None

    return uploads_playlist_id


def get_video_ids(uploads_playlist_id):

    video_ids = []

    next_page_token = None

    while True:

        request = youtube.playlistItems().list(
            part = "contentDetails",
            playlistId = uploads_playlist_id,
            maxResults = PLAYLIST_PAGE_SIZE,
            pageToken = next_page_token
        )

        response = execute_with_retry(
            request,
            f"Get playlist items {uploads_playlist_id}"
        )

        for item in response.get("items", []):

            content_details = item.get("contentDetails", {})

            video_id = content_details.get("videoId")

            if video_id:
                video_ids.append(video_id)

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

    logger.info(
        "Found %d video IDs in playlist %s",
        len(video_ids),
        uploads_playlist_id
    )

    return video_ids


def get_video_details(video_ids):

    videos = []

    if not video_ids:
        return videos

    for start in range(0, len(video_ids), VIDEO_BATCH_SIZE):

        batch = video_ids[start:start + VIDEO_BATCH_SIZE]

        logger.debug("Getting videos %d-%d", start, start+VIDEO_BATCH_SIZE)

        request = youtube.videos().list(
            part=(
                "snippet,"
                "contentDetails,"
                "statistics"
            ),
            id=",".join(batch)
        )

        response = execute_with_retry(
            request,
            "Get video details"
        )

        videos.extend(
            response.get("items", [])
        )

    logger.info(
        "Retrieved details for %d videos",
        len(videos)
    )

    return videos


def select_top_video(videos, limit = TOP_VIDEO_LIMIT):

    def get_view_count(video):
        statistics = video.get("statistics", {})

        return int(statistics.get("viewCount", 0))

    sorted_video = sorted(
        videos,
        key = get_view_count,
        reverse = True
    )

    top_videos = sorted_video[:limit]

    logger.info("Selected top %d videos", len(top_videos))

    return top_videos


def get_comments(video_id):

    comments = []
    next_page_token = None
    page_number = 0


    while page_number < MAX_COMMENT_PAGES:

        page_number += 1

        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=COMMENT_PAGE_SIZE,
            pageToken=next_page_token,
            textFormat="plainText"
        )

        try:
            response = execute_with_retry(
                request,
                f"Get comments for video {video_id}, page {page_number}"
            )

        except HttpError as e:
            logger.warning(
                "Cannot get comments for video %s. Skipping.",
                video_id
            )
            return []

        comments.extend(response.get("items", []))
        
    

        next_page_token = response.get(
            "nextPageToken"
        )

        if not next_page_token:
            break

    logger.info(
    "Retrieved %d comment threads for video %s",
    len(comments),
    video_id
    )  
    
    return comments

def flatten_video(video, artist_name):
    snippet = video.get("snippet", {})
    content_details = video.get("contentDetails", {})
    statistics = video.get("statistics", {})

    return {
        "artist_name": artist_name,
        "channel_id": snippet.get("channelId"),
        "channel_title": snippet.get("channelTitle"),
        "video_id": video.get("id"),
        "video_title": snippet.get("title"),
        "description": snippet.get("description"),
        "published_at": snippet.get("publishedAt"),
        "duration": content_details.get("duration"),
        "tags": snippet.get("tags", []),
        "category_id": snippet.get("categoryId"),
        "view_count": int(statistics.get("viewCount", 0)),
        "like_count": int(statistics.get("likeCount", 0)),
        "comment_count": int(statistics.get("commentCount", 0)),
    }


def flatten_comment(comment, artist_name, channel_id):
    thread_snippet = comment.get("snippet", {})

    top_comment = thread_snippet.get("topLevelComment", {})
    comment_snippet = top_comment.get("snippet", {})

    return {
        "artist_name": artist_name,
        "channel_id": channel_id,
        "video_id": thread_snippet.get("videoId"),
        "comment_id": top_comment.get("id"),
        "parent_id": None,
        "author_name": comment_snippet.get("authorDisplayName"),
        "comment_text": comment_snippet.get("textDisplay"),
        "published_at": comment_snippet.get("publishedAt"),
        "updated_at": comment_snippet.get("updatedAt"),
        "like_count": comment_snippet.get("likeCount", 0),
        "reply_count": thread_snippet.get("totalReplyCount", 0),
    }




def extract_artist(artist_name, channel_id, uploads_playlist_id):

    logger.info("Starting extraction for %s", artist_name)

    video_ids = get_video_ids(uploads_playlist_id)

    if not video_ids:
        logger.warning("No videos found for %s", artist_name)

        return{
            "video" : [],
            "comment" : []
        }

    videos = get_video_details(video_ids)

    top_videos = select_top_video(videos)

    comments = []

    for video in top_videos:

        video_id = video.get("id")

        if not video_id:
            continue

        video_comments = get_comments(
            video_id
        )

        comments.extend(
            video_comments
        )

    video_rows = [
        flatten_video(video, artist_name)
        for video in videos
    ]

    comment_rows = [
        flatten_comment(comment, artist_name, channel_id)
        for comment in comments
    ]


    videos_df = pd.DataFrame(video_rows)
    comments_df = pd.DataFrame(comment_rows)

    logger.info(
        "Finished extraction for %s: "
        "%d videos, %d comments",
        artist_name,
        len(videos),
        len(comments)
    )

    return {
        "videos": videos_df,
        "comments": comments_df
    }



def extract():

    artists = load_artists()

    for _, artist in artists.iterrows():

        artist_name = artist["artist_name"]
        channel_id = artist["channel_id"]
        uploads_playlist_id = get_uploads_playlist_id(channel_id)

        try:

            result = extract_artist(
                artist_name=artist_name,
                channel_id=channel_id,
                uploads_playlist_id=uploads_playlist_id
            )

            yield {
                "artist_name": artist_name,
                "channel_id": channel_id,
                "videos": result["videos"],
                "comments": result["comments"]
            }

        except HttpError as e:

            logger.error(
                "Artist %s failed: %s",
                artist_name,
                e
            )

            continue

        except Exception as e:

            logger.exception(
                "Unexpected error for artist %s: %s",
                artist_name,
                e
            )   

            continue

        
        

