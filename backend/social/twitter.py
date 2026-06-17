"""Post tweets via Twitter API v2 (OAuth 1.0a user context)."""
import io
import os

_ENABLED: bool | None = None
_CLIENT = None
_API_V1 = None


def _init():
    global _ENABLED, _CLIENT, _API_V1
    if _ENABLED is not None:
        return

    key     = os.getenv("TWITTER_CONSUMER_KEY", "")
    secret  = os.getenv("TWITTER_CONSUMER_SECRET", "")
    token   = os.getenv("TWITTER_ACCESS_TOKEN", "")
    tsecret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")

    if not all([key, secret, token, tsecret]):
        _ENABLED = False
        return

    try:
        import tweepy
        _CLIENT = tweepy.Client(
            consumer_key=key,
            consumer_secret=secret,
            access_token=token,
            access_token_secret=tsecret,
        )
        auth = tweepy.OAuth1UserHandler(key, secret, token, tsecret)
        _API_V1 = tweepy.API(auth)
        _ENABLED = True
    except Exception as exc:
        print(f"[Twitter] Failed to initialise client: {exc}")
        _ENABLED = False


def is_enabled() -> bool:
    _init()
    return _ENABLED is True


def _upload_image(image_url: str) -> str | None:
    if not image_url:
        return None
    try:
        import httpx
        resp = httpx.get(image_url, follow_redirects=True, timeout=10, verify=False)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/jpeg")
        ext = "png" if "png" in content_type else "gif" if "gif" in content_type else "jpg"
        media = _API_V1.media_upload(filename=f"image.{ext}", file=io.BytesIO(resp.content))
        return str(media.media_id)
    except Exception as exc:
        print(f"[Twitter] Failed to upload image: {exc}")
        return None


def post_tweet(text: str, image_url: str = "") -> bool:
    _init()
    if not _CLIENT:
        return False
    try:
        media_ids = None
        if image_url:
            media_id = _upload_image(image_url)
            if media_id:
                media_ids = [media_id]
        _CLIENT.create_tweet(text=text, media_ids=media_ids)
        return True
    except Exception as exc:
        print(f"[Twitter] Failed to post tweet: {exc}")
        return False
