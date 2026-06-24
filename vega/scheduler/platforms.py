"""
scheduler/platforms.py — Vega
Platform API contracts for Instagram, TikTok, YouTube, Facebook, LinkedIn, X.
Each platform has a publish() method and a get_metrics() method.

Rule 13: These methods call real APIs. They don't fake success.
         If the API key isn't set, they raise clearly. (Rule 6)
Rule 12: All credentials come from environment variables. Never hardcoded.

Author: Everett Christman / The Christman AI Project
Cardinal Rules: All 15 apply. Rule 13 is gospel.
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger("vega.scheduler.platforms")


class PlatformBase(ABC):
    """Abstract base for all platform integrations."""

    def __init__(self, platform_name: str, required_env_vars: list[str]):
        self.platform_name = platform_name
        self._check_env(required_env_vars)

    def _check_env(self, required_vars: list[str]) -> None:
        missing = [v for v in required_vars if not os.environ.get(v)]
        if missing:
            raise EnvironmentError(
                f"[Vega.{self.platform_name}] Missing env vars: {missing}. "
                "Add them to .env (Rule 12: no secrets in source)"
            )

    @abstractmethod
    def publish_video(self, file_path: str, caption: str, **kwargs) -> dict:
        """Publish a video post. Returns {"status", "post_id", "url"}"""

    @abstractmethod
    def publish_image(self, file_path: str, caption: str, **kwargs) -> dict:
        """Publish an image post. Returns {"status", "post_id", "url"}"""

    @abstractmethod
    def get_metrics(self, post_id: str) -> dict:
        """Fetch real engagement metrics for a post."""


# ── Instagram ─────────────────────────────────────────────────────────────────

class InstagramPlatform(PlatformBase):
    """Instagram Graph API v18.0"""

    def __init__(self):
        super().__init__("Instagram", ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID"])
        self.access_token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
        self.account_id = os.environ["INSTAGRAM_ACCOUNT_ID"]

    def publish_video(self, file_path: str, caption: str, **kwargs) -> dict:
        """
        Publish a Reel to Instagram.
        Flow: upload → create container → publish
        Rule 13: Returns real post_id from API or raises.
        """
        try:
            import requests

            if not Path(file_path).exists():
                return {"status": "error", "reason": f"File not found: {file_path}"}

            # Step 1: Create video container
            container_url = f"https://graph.facebook.com/v18.0/{self.account_id}/media"
            container_resp = requests.post(container_url, data={
                "media_type": "REELS",
                "video_url": file_path,  # Must be publicly accessible URL in production
                "caption": caption,
                "access_token": self.access_token,
            })
            container_resp.raise_for_status()
            container_id = container_resp.json()["id"]

            # Step 2: Publish
            publish_url = f"https://graph.facebook.com/v18.0/{self.account_id}/media_publish"
            publish_resp = requests.post(publish_url, data={
                "creation_id": container_id,
                "access_token": self.access_token,
            })
            publish_resp.raise_for_status()
            post_id = publish_resp.json()["id"]

            logger.info(f"[Vega.Instagram] Published video: {post_id}")
            return {
                "status": "published",
                "platform": "instagram",
                "post_id": post_id,
                "url": f"https://www.instagram.com/p/{post_id}/",
            }
        except Exception as e:
            logger.error(f"[Vega.Instagram] Publish failed: {e}")
            return {"status": "error", "reason": str(e)}

    def publish_image(self, file_path: str, caption: str, **kwargs) -> dict:
        try:
            import requests

            container_url = f"https://graph.facebook.com/v18.0/{self.account_id}/media"
            container_resp = requests.post(container_url, data={
                "image_url": file_path,
                "caption": caption,
                "access_token": self.access_token,
            })
            container_resp.raise_for_status()
            container_id = container_resp.json()["id"]

            publish_url = f"https://graph.facebook.com/v18.0/{self.account_id}/media_publish"
            publish_resp = requests.post(publish_url, data={
                "creation_id": container_id,
                "access_token": self.access_token,
            })
            publish_resp.raise_for_status()
            post_id = publish_resp.json()["id"]

            return {"status": "published", "platform": "instagram", "post_id": post_id}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def get_metrics(self, post_id: str) -> dict:
        try:
            import requests
            url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
            resp = requests.get(url, params={
                "metric": "impressions,reach,likes_count,comments_count,shares",
                "access_token": self.access_token,
            })
            resp.raise_for_status()
            data = resp.json().get("data", [])
            metrics = {item["name"]: item["values"][0]["value"] for item in data if item.get("values")}
            return {"status": "ok", "platform": "instagram", "post_id": post_id, "metrics": metrics}
        except Exception as e:
            return {"status": "error", "reason": str(e)}


# ── YouTube ───────────────────────────────────────────────────────────────────

class YouTubePlatform(PlatformBase):
    """YouTube Data API v3"""

    def __init__(self):
        super().__init__("YouTube", ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"])

    def _get_access_token(self) -> str:
        import requests
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": os.environ["YOUTUBE_CLIENT_ID"],
            "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
            "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        return resp.json()["access_token"]

    def publish_video(self, file_path: str, caption: str, title: str = "Christman AI Project", **kwargs) -> dict:
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.oauth2.credentials import Credentials

            creds = Credentials(
                token=self._get_access_token(),
                client_id=os.environ["YOUTUBE_CLIENT_ID"],
                client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
            )
            youtube = build("youtube", "v3", credentials=creds)

            body = {
                "snippet": {
                    "title": title,
                    "description": caption,
                    "tags": ["ChristmanAIProject", "LumaCognifyAI"],
                    "categoryId": "22",
                },
                "status": {"privacyStatus": kwargs.get("privacy", "public")},
            }

            media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
            response = request.execute()

            post_id = response["id"]
            logger.info(f"[Vega.YouTube] Uploaded video: {post_id}")
            return {
                "status": "published",
                "platform": "youtube",
                "post_id": post_id,
                "url": f"https://www.youtube.com/watch?v={post_id}",
            }
        except ImportError:
            return {"status": "error", "reason": "google-api-python-client not installed"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def publish_image(self, file_path: str, caption: str, **kwargs) -> dict:
        # YouTube doesn't support standalone image posts — upload as Community post
        return {
            "status": "skipped",
            "reason": "YouTube does not support standalone image posts. Use publish_video for video content.",
            "platform": "youtube",
        }

    def get_metrics(self, post_id: str) -> dict:
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials

            creds = Credentials(token=self._get_access_token())
            youtube = build("youtube", "v3", credentials=creds)

            response = youtube.videos().list(
                part="statistics",
                id=post_id,
            ).execute()

            if not response.get("items"):
                return {"status": "error", "reason": f"Video {post_id} not found"}

            stats = response["items"][0]["statistics"]
            return {
                "status": "ok",
                "platform": "youtube",
                "post_id": post_id,
                "metrics": {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                },
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}


# ── TikTok ────────────────────────────────────────────────────────────────────

class TikTokPlatform(PlatformBase):
    """TikTok Content Posting API v2"""

    def __init__(self):
        super().__init__("TikTok", ["TIKTOK_ACCESS_TOKEN"])
        self.access_token = os.environ["TIKTOK_ACCESS_TOKEN"]

    def publish_video(self, file_path: str, caption: str, **kwargs) -> dict:
        try:
            import requests

            # Step 1: Init upload
            init_resp = requests.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                json={
                    "post_info": {"title": caption[:150], "privacy_level": "PUBLIC_TO_EVERYONE"},
                    "source_info": {"source": "FILE_UPLOAD", "video_size": Path(file_path).stat().st_size},
                }
            )
            init_resp.raise_for_status()
            data = init_resp.json().get("data", {})
            publish_id = data.get("publish_id")
            upload_url = data.get("upload_url")

            if not upload_url:
                return {"status": "error", "reason": "TikTok did not return upload URL"}

            # Step 2: Upload file
            with open(file_path, "rb") as f:
                upload_resp = requests.put(upload_url, data=f)
            upload_resp.raise_for_status()

            return {"status": "published", "platform": "tiktok", "post_id": publish_id}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def publish_image(self, file_path: str, caption: str, **kwargs) -> dict:
        try:
            import requests
            # TikTok photo posts via Content Posting API
            resp = requests.post(
                "https://open.tiktokapis.com/v2/post/publish/content/init/",
                headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                json={
                    "post_info": {"title": caption[:150], "privacy_level": "PUBLIC_TO_EVERYONE"},
                    "source_info": {"source": "FILE_UPLOAD", "photo_cover_index": 0,
                                    "photo_images": [file_path]},
                    "post_mode": "DIRECT_POST",
                    "media_type": "PHOTO",
                }
            )
            resp.raise_for_status()
            return {"status": "published", "platform": "tiktok", "post_id": resp.json().get("data", {}).get("publish_id")}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def get_metrics(self, post_id: str) -> dict:
        try:
            import requests
            resp = requests.post(
                "https://open.tiktokapis.com/v2/video/query/",
                headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
                json={"filters": {"video_ids": [post_id]},
                      "fields": ["id", "like_count", "comment_count", "share_count", "view_count"]},
            )
            resp.raise_for_status()
            videos = resp.json().get("data", {}).get("videos", [])
            if not videos:
                return {"status": "error", "reason": f"Video {post_id} not found"}
            v = videos[0]
            return {
                "status": "ok",
                "platform": "tiktok",
                "post_id": post_id,
                "metrics": {
                    "views": v.get("view_count", 0),
                    "likes": v.get("like_count", 0),
                    "comments": v.get("comment_count", 0),
                    "shares": v.get("share_count", 0),
                },
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}


# ── X (Twitter) ───────────────────────────────────────────────────────────────

class XPlatform(PlatformBase):
    """X (Twitter) API v2"""

    def __init__(self):
        super().__init__("X", ["X_BEARER_TOKEN", "X_API_KEY", "X_API_SECRET",
                               "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"])

    def _get_client(self):
        import tweepy
        return tweepy.Client(
            bearer_token=os.environ["X_BEARER_TOKEN"],
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
        )

    def publish_video(self, file_path: str, caption: str, **kwargs) -> dict:
        try:
            import tweepy
            auth = tweepy.OAuth1UserHandler(
                os.environ["X_API_KEY"], os.environ["X_API_SECRET"],
                os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_TOKEN_SECRET"],
            )
            api = tweepy.API(auth)
            media = api.media_upload(filename=file_path, media_category="tweet_video")
            client = self._get_client()
            tweet = client.create_tweet(text=caption[:280], media_ids=[media.media_id_string])
            return {"status": "published", "platform": "x", "post_id": tweet.data["id"]}
        except ImportError:
            return {"status": "error", "reason": "tweepy not installed. pip install tweepy"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def publish_image(self, file_path: str, caption: str, **kwargs) -> dict:
        try:
            import tweepy
            auth = tweepy.OAuth1UserHandler(
                os.environ["X_API_KEY"], os.environ["X_API_SECRET"],
                os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_TOKEN_SECRET"],
            )
            api = tweepy.API(auth)
            media = api.media_upload(filename=file_path)
            client = self._get_client()
            tweet = client.create_tweet(text=caption[:280], media_ids=[media.media_id_string])
            return {"status": "published", "platform": "x", "post_id": tweet.data["id"]}
        except ImportError:
            return {"status": "error", "reason": "tweepy not installed"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def get_metrics(self, post_id: str) -> dict:
        try:
            client = self._get_client()
            tweet = client.get_tweet(post_id, tweet_fields=["public_metrics"])
            metrics = tweet.data.public_metrics
            return {
                "status": "ok",
                "platform": "x",
                "post_id": post_id,
                "metrics": {
                    "views": metrics.get("impression_count", 0),
                    "likes": metrics.get("like_count", 0),
                    "comments": metrics.get("reply_count", 0),
                    "shares": metrics.get("retweet_count", 0),
                },
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}


# ── LinkedIn ──────────────────────────────────────────────────────────────────

class LinkedInPlatform(PlatformBase):
    """LinkedIn Marketing API"""

    def __init__(self):
        super().__init__("LinkedIn", ["LINKEDIN_ACCESS_TOKEN", "LINKEDIN_AUTHOR_ID"])
        self.access_token = os.environ["LINKEDIN_ACCESS_TOKEN"]
        self.author_id = os.environ["LINKEDIN_AUTHOR_ID"]  # urn:li:person:xxx or urn:li:organization:xxx

    def publish_video(self, file_path: str, caption: str, **kwargs) -> dict:
        return {
            "status": "error",
            "reason": "LinkedIn video upload requires a multi-step upload flow. "
                      "Not yet implemented. (Rule 13: honest about gaps)",
            "platform": "linkedin",
        }

    def publish_image(self, file_path: str, caption: str, **kwargs) -> dict:
        try:
            import requests

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }

            # Register upload
            register_resp = requests.post(
                "https://api.linkedin.com/v2/assets?action=registerUpload",
                headers=headers,
                json={
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": self.author_id,
                        "serviceRelationships": [
                            {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
                        ],
                    }
                }
            )
            register_resp.raise_for_status()
            asset = register_resp.json()["value"]["asset"]
            upload_url = register_resp.json()["value"]["uploadMechanism"][
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
            ]["uploadUrl"]

            # Upload image
            with open(file_path, "rb") as f:
                requests.put(upload_url, data=f, headers={"Authorization": f"Bearer {self.access_token}"})

            # Create post
            post_resp = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json={
                    "author": self.author_id,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": caption},
                            "shareMediaCategory": "IMAGE",
                            "media": [{"status": "READY", "media": asset}],
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
                }
            )
            post_resp.raise_for_status()
            post_id = post_resp.json()["id"]
            return {"status": "published", "platform": "linkedin", "post_id": post_id}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def get_metrics(self, post_id: str) -> dict:
        try:
            import requests
            resp = requests.get(
                f"https://api.linkedin.com/v2/socialMetrics/{post_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "ok",
                "platform": "linkedin",
                "post_id": post_id,
                "metrics": {
                    "likes": data.get("totalSocialActivityCounts", {}).get("numLikes", 0),
                    "comments": data.get("totalSocialActivityCounts", {}).get("numComments", 0),
                    "shares": data.get("totalSocialActivityCounts", {}).get("numShares", 0),
                },
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}


# ── Facebook ──────────────────────────────────────────────────────────────────

class FacebookPlatform(PlatformBase):
    """Facebook Graph API v18.0"""

    def __init__(self):
        super().__init__("Facebook", ["FACEBOOK_ACCESS_TOKEN", "FACEBOOK_PAGE_ID"])
        self.access_token = os.environ["FACEBOOK_ACCESS_TOKEN"]
        self.page_id = os.environ["FACEBOOK_PAGE_ID"]

    def publish_video(self, file_path: str, caption: str, **kwargs) -> dict:
        try:
            import requests
            url = f"https://graph-video.facebook.com/v18.0/{self.page_id}/videos"
            with open(file_path, "rb") as f:
                resp = requests.post(url, data={
                    "description": caption,
                    "access_token": self.access_token,
                }, files={"source": f})
            resp.raise_for_status()
            post_id = resp.json().get("id")
            return {"status": "published", "platform": "facebook", "post_id": post_id}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def publish_image(self, file_path: str, caption: str, **kwargs) -> dict:
        try:
            import requests
            url = f"https://graph.facebook.com/v18.0/{self.page_id}/photos"
            with open(file_path, "rb") as f:
                resp = requests.post(url, data={
                    "message": caption,
                    "access_token": self.access_token,
                }, files={"source": f})
            resp.raise_for_status()
            post_id = resp.json().get("id")
            return {"status": "published", "platform": "facebook", "post_id": post_id}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def get_metrics(self, post_id: str) -> dict:
        try:
            import requests
            resp = requests.get(
                f"https://graph.facebook.com/v18.0/{post_id}/insights",
                params={
                    "metric": "post_impressions,post_reactions_by_type_total,post_clicks",
                    "access_token": self.access_token,
                }
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            metrics = {item["name"]: item["values"][0]["value"] for item in data if item.get("values")}
            return {"status": "ok", "platform": "facebook", "post_id": post_id, "metrics": metrics}
        except Exception as e:
            return {"status": "error", "reason": str(e)}


# ── Platform Factory ──────────────────────────────────────────────────────────

def get_platform(name: str) -> PlatformBase:
    """
    Return the platform instance for a given platform name.
    Raises clearly if platform isn't supported. (Rule 6)
    """
    platforms = {
        "instagram": InstagramPlatform,
        "youtube": YouTubePlatform,
        "tiktok": TikTokPlatform,
        "x": XPlatform,
        "linkedin": LinkedInPlatform,
        "facebook": FacebookPlatform,
    }
    name_lower = name.lower()
    if name_lower not in platforms:
        raise ValueError(
            f"Platform '{name}' not supported. "
            f"Vega supports: {', '.join(platforms.keys())}"
        )
    return platforms[name_lower]()
