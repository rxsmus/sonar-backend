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


CLIENT_ID = "51dd9a50cd994a7e8e374fc2169c6f25"
CLIENT_SECRET = "9b0bbe25c87d457184ef9e12b5e876fd"
SCOPE = "user-read-currently-playing user-read-playback-state user-read-private user-read-email"
REDIRECT_URI = (
    "https://spotcord-1.onrender.com/callback"  # Should match your Render URL
)


def get_spotify_client():
    token_info = session.get("token_info")
    if not token_info:
        return None
    # Refresh token if needed
    oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
    )
    if oauth.is_token_expired(token_info):
        token_info = oauth.refresh_access_token(token_info["refresh_token"])
        session["token_info"] = token_info
    return spotipy.Spotify(auth=token_info["access_token"])



# Spotify OAuth callback: exchange code for tokens and store in session
@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Missing code", 400
    oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
    )
    token_info = oauth.get_access_token(code, as_dict=True)
    if not token_info or "access_token" not in token_info:
        return "Failed to get token", 400
    session["token_info"] = token_info
    # Redirect to frontend (remove code from URL)
    frontend_url = "https://spotcord-frontend.vercel.app/"
    return redirect(frontend_url)

# Get current playing track for logged-in user
@app.route("/listening")
def listening():
    spotify = get_spotify_client()
    if not spotify:
        return jsonify({"is_playing": False, "error": "Not authenticated"}), 401
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



# Endpoint to get Spotify user info (username, id)
@app.route("/spotify_user")
def spotify_user():
    spotify = get_spotify_client()
    if not spotify:
        return jsonify({"error": "Not authenticated"}), 401
    user = spotify.current_user()
    return jsonify({
        "id": user.get("id"),
        "display_name": user.get("display_name"),
        "images": user.get("images", []),
        "email": user.get("email"),
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3112, debug=True)
