"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    # ---------------------------------------------------------------
    # Taste profiles — pick one (or add your own) to test the system.
    #
    # Each key maps directly to a feature in songs.csv.
    # Continuous values (energy, valence, etc.) are scored by proximity:
    #   score = 1 - |user_target - song_value|
    # so set them to what you actually want, not what sounds "high."
    # ---------------------------------------------------------------

    # Profile A — Late-night lo-fi study session
    # Wants: calm, acoustic, instrumental, focused, no hype
    late_night_studier = {
        "name": "Late-Night Studier",
        "genre": "lofi",
        "mood": "focused",
        "target_energy": 0.38,          # low intensity — background music only
        "target_valence": 0.58,         # neutral emotional tone, not sad or euphoric
        "target_tempo_bpm": 76,         # slow and steady
        "target_acousticness": 0.82,    # strongly prefers organic / non-electronic texture
        "target_danceability": 0.58,    # mild rhythmic feel is fine
        "target_speechiness": 0.03,     # no lyrics, purely instrumental preferred
        "target_instrumentalness": 0.88,  # wants tracks with no vocals
    }

    # Profile B — Morning workout
    # Wants: high energy, upbeat, fast tempo, driveable beat
    # mood changed from "energetic" → "intense": "energetic" has no pop match
    # in the catalog, so the old profile was chasing a ghost combination.
    morning_runner = {
        "name": "Morning Runner",
        "genre": "pop",
        "mood": "intense",
        "target_energy": 0.92,          # near maximum — needs to push through the burn
        "target_valence": 0.80,         # upbeat and positive, not dark or aggressive
        "target_tempo_bpm": 132,        # fast enough to match a running cadence
        "target_acousticness": 0.06,    # electronic / produced sound preferred
        "target_danceability": 0.88,    # strong driving beat matters
        "target_speechiness": 0.07,     # some vocal energy is fine
        "target_instrumentalness": 0.02,  # wants a vocalist hyping them up
    }

    # Profile C — Sunday evening wind-down
    # Wants: mellow, warm, a touch melancholic, acoustic texture
    sunday_wind_down = {
        "name": "Sunday Wind-Down",
        "genre": "folk",
        "mood": "melancholic",
        "target_energy": 0.32,          # quiet and unhurried
        "target_valence": 0.36,         # bittersweet — not fully dark, not cheerful
        "target_tempo_bpm": 70,         # slow, contemplative pace
        "target_acousticness": 0.90,    # acoustic guitar / piano texture strongly preferred
        "target_danceability": 0.44,    # gentle sway, not a dance track
        "target_speechiness": 0.07,     # light lyrical presence is welcome
        "target_instrumentalness": 0.12,  # vocals matter — singer-songwriter style
    }

    # Active profile — swap in any of the three above
    user_prefs = late_night_studier

    recommendations = recommend_songs(user_prefs, songs, k=5)

    # ---------------------------------------------------------------
    # Terminal output — clean, readable layout
    # Shows: rank, title, artist, score out of MAX_SCORE, and every
    # reason produced by score_song() on its own indented line.
    # ---------------------------------------------------------------
    from recommender import MAX_SCORE

    print(f"\n{'='*60}")
    print(f"  Music Recommender — Top 5 for: {user_prefs['name']}")
    print(f"  Taste: {user_prefs['genre']} / {user_prefs['mood']}")
    print(f"{'='*60}\n")

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"#{rank}  {song['title']}  —  {song['artist']}")
        print(f"    Score: {score:.2f} / {MAX_SCORE:.2f}")
        print(f"    Why:")
        for reason in explanation.split("; "):
            print(f"      • {reason}")
        print()


if __name__ == "__main__":
    main()
