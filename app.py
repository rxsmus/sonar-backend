from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheHandler
import threading
from datetime import datetime


app = Flask(__name__)
# Allow specific origins (frontend and socket server). In production, set this
# to your exact frontend host. We allow both the Vercel frontend and the
# onrender socket host used by the project.
allowed_origins = [
    "https://spotcord-frontend.vercel.app",
    "https://spotcord.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS(app, origins=allowed_origins, supports_credentials=True)


# Redirect from /callback to frontend after Spotify auth
@app.route("/callback")
def callback():
    # Optionally, you could process the code here if needed
    # Redirect to frontend with code as query parameter
    code = request.args.get("code")
    # If we have a code, exchange it here and cache token server-side so
    # subsequent /refresh calls can return an access token for the SDK.
    if code:
        try:
            cache_handler = SessionCacheHandler(code)
            oauth = SpotifyOAuth(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                scope=SCOPE,
                cache_handler=cache_handler,
            )
            # Exchange code for token and let SpotifyOAuth save to our cache handler
            token_info = oauth.get_access_token(code, as_dict=True)
            print(f"[DEBUG] Exchanged code and cached token for code: {code}")
            try:
                print(f"[DEBUG] token_info scopes: {token_info.get('scope')}")
            except Exception:
                pass
        except Exception as e:
            print(f"[DEBUG] Error exchanging code in callback: {e}")

    frontend_url = (
        f"https://spotcord-frontend.vercel.app/?code={code}"
        if code
        else "https://spotcord-frontend.vercel.app/"
    )
    return redirect(frontend_url)


CLIENT_ID = "51dd9a50cd994a7e8e374fc2169c6f25"
CLIENT_SECRET = "9b0bbe25c87d457184ef9e12b5e876fd"
SCOPE = "streaming user-read-currently-playing user-read-playback-state user-modify-playback-state user-read-private"
REDIRECT_URI = (
    "https://spotcord-1.onrender.com/callback"  # Should match your Render URL
)


_session_token_cache = {}
_session_token_cache_lock = threading.Lock()


class SessionCacheHandler(CacheHandler):
    def __init__(self, code):
        self.code = code

    def get_cached_token(self):
        with _session_token_cache_lock:
            return _session_token_cache.get(self.code)

    def save_token_to_cache(self, token_info):
        with _session_token_cache_lock:
            _session_token_cache[self.code] = token_info


def get_spotify_client(code):
    print(f"[DEBUG] get_spotify_client called with code: {code}")
    # Reject missing, empty, or placeholder codes
    if not code or code.strip() == "" or code == "YOUR_SPOTIFY_CODE":
        print("[DEBUG] Invalid or placeholder code received.")
        return None
    try:
        cache_handler = SessionCacheHandler(code)
        oauth = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            cache_handler=cache_handler,
        )
        token_info = oauth.get_cached_token()
        if not token_info:
            token_info = oauth.get_access_token(code, as_dict=True)
        try:
            print(
                f"[DEBUG] token_info scopes (get_spotify_client): {token_info.get('scope')}"
            )
        except Exception:
            pass

        # If token exists but expired, attempt to refresh using the refresh_token
        if (
            token_info
            and "expires_at" in token_info
            and token_info["expires_at"] < int(datetime.now().timestamp())
        ):
            print(f"[DEBUG] Access token expired for code: {code}, attempting refresh")
            try:
                refresh_token = token_info.get("refresh_token")
                if refresh_token:
                    new_token_info = oauth.refresh_access_token(refresh_token)
                    # Ensure the cache is updated
                    cache_handler.save_token_to_cache(new_token_info)
                    token_info = new_token_info
                else:
                    print("[DEBUG] No refresh token available; cannot refresh")
                    return None
            except Exception as e:
                print(f"[DEBUG] Exception refreshing token: {e}")
                return None

        # Validate token_info structure and token expiration
        if (
            not token_info
            or "access_token" not in token_info
            or not token_info["access_token"]
        ):
            print(f"[DEBUG] No valid access token for code: {code}")
            return None
        # Optionally, validate token by fetching user profile
        try:
            spotify = spotipy.Spotify(auth=token_info["access_token"])
            user = spotify.current_user()
            if not user or "id" not in user:
                print(f"[DEBUG] Token did not yield a valid user for code: {code}")
                return None
            return spotify
        except Exception as e:
            print(f"[DEBUG] Exception validating token: {e}")
            return None
    except Exception as e:
        print(f"[DEBUG] Exception in get_spotify_client: {e}")
        return None


@app.route("/listening")
def listening():
    code = request.args.get("code")
    print(f"[DEBUG] /listening called with code: {code}")
    spotify = get_spotify_client(code)
    if spotify is None:
        print("[DEBUG] Invalid Spotify client. Returning 401.")
        return (
            jsonify(
                {
                    "is_playing": False,
                    "error": "Not authenticated or code missing/expired",
                }
            ),
            401,
        )
    try:
        current_track = spotify.current_user_playing_track()
        if not current_track or not current_track.get("is_playing"):
            return jsonify({"is_playing": False})
        item = current_track["item"]
        track_name = item["name"]
        artists = ", ".join(artist["name"] for artist in item["artists"])
        album_name = item["album"]["name"]
        album_image_url = item["album"]["images"][0]["url"]
        track_id = item["id"]
        return jsonify(
            {
                "is_playing": True,
                "track_name": track_name,
                "artists": artists,
                "album_name": album_name,
                "album_image_url": album_image_url,
                "track_id": track_id,
            }
        )
    except Exception as e:
        return (
            jsonify({"is_playing": False, "error": f"Spotify API error: {str(e)}"}),
            400,
        )


# Endpoint to get Spotify user info (username, id)
@app.route("/spotify_user")
def spotify_user():
    code = request.args.get("code")
    print(f"[DEBUG] /spotify_user called with code: {code}")
    spotify = get_spotify_client(code)
    if spotify is None:
        print("[DEBUG] Invalid Spotify client for user info. Returning 401.")
        return jsonify({"error": "Not authenticated or code missing/expired"}), 401
    try:
        user = spotify.current_user()
        print(
            f"[DEBUG] Spotify user id: {user.get('id')}, display_name: {user.get('display_name')}"
        )
        user_info = {
            "id": user.get("id"),
            "display_name": user.get("display_name"),
            "images": user.get("images", []),
        }
        return jsonify(user_info)
    except Exception as e:
        return jsonify({"error": f"Spotify API error: {str(e)}"}), 400


@app.route("/refresh")
def refresh_token():
    """Return a fresh access token for the given code if possible.
    Frontend should call this to get a short-lived access token for the Web Playback SDK.
    """
    code = request.args.get("code")
    print(f"[DEBUG] /refresh called with code: {code}")
    if not code:
        return jsonify({"error": "code missing"}), 400
    try:
        cache_handler = SessionCacheHandler(code)
        oauth = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            cache_handler=cache_handler,
        )
        token_info = oauth.get_cached_token()
        if not token_info:
            return jsonify({"error": "No token cached for this code"}), 401
        # Refresh if expired
        if "expires_at" in token_info and token_info["expires_at"] < int(
            datetime.now().timestamp()
        ):
            refresh_token = token_info.get("refresh_token")
            if not refresh_token:
                return jsonify({"error": "No refresh token available"}), 401
            try:
                new_token_info = oauth.refresh_access_token(refresh_token)
                cache_handler.save_token_to_cache(new_token_info)
                token_info = new_token_info
            except Exception as e:
                print(f"[DEBUG] Error refreshing token in /refresh: {e}")
                return jsonify({"error": f"Refresh failed: {str(e)}"}), 400

        return jsonify(
            {
                "access_token": token_info.get("access_token"),
                "expires_at": token_info.get("expires_at"),
                "scope": token_info.get("scope"),
            }
        )
    except Exception as e:
        print(f"[DEBUG] Exception in /refresh: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3112, debug=True)
