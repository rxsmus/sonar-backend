from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime


app = Flask(__name__)
CORS(
    app, supports_credentials=True
)  # allow frontend (React) to make requests to backend


# Redirect from /callback to frontend after Spotify auth
@app.route("/callback")
def callback():
    # Optionally, you could process the code here if needed
    # Redirect to frontend with code as query parameter
    code = request.args.get("code")
    frontend_url = (
        f"https://spotcord-frontend.vercel.app/?code={code}"
        if code
        else "https://spotcord-frontend.vercel.app/"
    )
    return redirect(frontend_url)


CLIENT_ID = "51dd9a50cd994a7e8e374fc2169c6f25"
CLIENT_SECRET = "9b0bbe25c87d457184ef9e12b5e876fd"
SCOPE = "user-read-currently-playing user-read-playback-state user-read-private"
REDIRECT_URI = (
    "https://spotcord-1.onrender.com/callback"  # Should match your Render URL
)


def get_spotify_client(code):
    print(f"[DEBUG] get_spotify_client called with code: {code}")
    # Reject missing, empty, or placeholder codes
    if not code or code.strip() == "" or code == "YOUR_SPOTIFY_CODE":
        print("[DEBUG] Invalid or placeholder code received.")
        return None
    try:
        oauth = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            cache_path=None,
        )
        token_info = oauth.get_access_token(code, as_dict=True)
        # Validate token_info structure and token expiration
        if (
            not token_info
            or "access_token" not in token_info
            or not token_info["access_token"]
            or ("expires_at" in token_info and token_info["expires_at"] < int(datetime.now().timestamp()))
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
        return jsonify({"is_playing": False, "error": "Not authenticated or code missing/expired"}), 401
    try:
        current_track = spotify.current_user_playing_track()
        if not current_track or not current_track.get("is_playing"):
            return jsonify({"is_playing": False})
        item = current_track["item"]
        track_name = item["name"]
        artists = ", ".join(artist["name"] for artist in item["artists"])
        album_name = item["album"]["name"]
        album_image_url = item["album"]["images"][0]["url"]
        progress_ms = current_track["progress_ms"]
        duration_ms = item["duration_ms"]
        progress = datetime.utcfromtimestamp(progress_ms / 1000).strftime("%M:%S")
        duration = datetime.utcfromtimestamp(duration_ms / 1000).strftime("%M:%S")
        track_id = item["id"]
        return jsonify(
            {
                "is_playing": True,
                "track_name": track_name,
                "artists": artists,
                "album_name": album_name,
                "album_image_url": album_image_url,
                "progress": progress,
                "duration": duration,
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3112, debug=True)
