@echo off
echo Installing spotdl without conflicting FastAPI dependency...
pip install spotdl --no-deps
pip install beautifulsoup4 mutagen rapidfuzz requests rich yt-dlp ytmusicapi spotipy syncedlyrics platformdirs python-slugify pydantic jinja2 websockets
echo Done. Restart WaveMash.
