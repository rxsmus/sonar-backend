from flask import Flask, jsonify
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime

app = Flask(__name__)
CORS(app)  # allow frontend (React) to make requests to backend

spotify = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id="51dd9a50cd994a7e8e374fc2169c6f25",
        client_secret="9b0bbe25c87d457184ef9e12b5e876fd",
        redirect_uri="http://127.0.0.1:9090",
        scope="user-read-currently-playing user-read-playback-state",
    )
)

@app.route("/listening")
def listening():
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

    return jsonify({
        "is_playing": True,
        "track_name": track_name,
        "artists": artists,
        "album_name": album_name,
        "album_image_url": album_image_url,
        "progress": progress,
        "duration": duration,
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3112, debug=True)
