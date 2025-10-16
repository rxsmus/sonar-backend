from flask import Flask, jsonify, request, session, redirect
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime


app = Flask(__name__)
app.secret_key = "spotcord_secret_key"  # Change this in production
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
    if not code:
        return None
    try:
        oauth = SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
        )
        token_info = oauth.get_access_token(code, as_dict=True)
        if not token_info or "access_token" not in token_info:
            return None
        return spotipy.Spotify(auth=token_info["access_token"])
    except Exception as e:
        return str(e)


@app.route("/listening")
def listening():
    code = request.args.get("code")
    spotify = get_spotify_client(code)
    if spotify is None:
        return (
            jsonify(
                {
                    "is_playing": False,
                    "error": "Not authenticated or code missing/expired",
                }
            ),
            401,
        )
    if isinstance(spotify, str):
        return jsonify({"is_playing": False, "error": f"Spotify error: {spotify}"}), 400
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
    spotify = get_spotify_client(code)
    if spotify is None:
        return jsonify({"error": "Not authenticated or code missing/expired"}), 401
    if isinstance(spotify, str):
        return jsonify({"error": f"Spotify error: {spotify}"}), 400
    try:
        user = spotify.current_user()
        return jsonify(
            {
                "id": user.get("id"),
                "display_name": user.get("display_name"),
                "images": user.get("images", []),
                "email": user.get("email"),
            }
        )
    except Exception as e:
        return jsonify({"error": f"Spotify API error: {str(e)}"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3112, debug=True)
