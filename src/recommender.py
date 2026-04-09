import csv
from dataclasses import dataclass
from typing import List, Dict, Tuple

# ---------------------------------------------------------------------------
# Algorithm Recipe — point budget
# ---------------------------------------------------------------------------
#
# Each feature contributes a maximum number of points toward a song's total.
# The maximum possible score is 7.75 points (a perfect match on every feature).
#
# Categorical features (binary match):
#   Genre  +2.00  — hard taste boundary; mismatches are near-automatic rejections
#   Mood   +1.50  — strong intent signal; raised from a common 1.0 starter so
#                   that a correct mood can tip a close genre contest
#
# Continuous features (proximity scoring):
#   points = max_points × (1 − |user_target − song_value|)
#   A score of 1.0 is as valid as 0.0 — closeness is what matters, not magnitude.
#
#   Energy          up to +1.50  — most powerful vibe signal (same budget as mood)
#   Valence         up to +1.00  — emotional tone: dark vs bright
#   Tempo           up to +0.75  — activity context: running pace vs study pace
#   Acousticness    up to +0.50  — texture: organic vs electronic
#   Speechiness     up to +0.25  — vocal density: sung vs rapped vs instrumental
#   Instrumentalness up to +0.25 — no-vocals preference; pairs with speechiness
#
# Max total: 2.00 + 1.50 + 1.50 + 1.00 + 0.75 + 0.50 + 0.25 + 0.25 = 7.75 pts
# ---------------------------------------------------------------------------
_POINTS: Dict[str, float] = {
    "genre":             2.00,
    "mood":              1.50,
    "energy":            1.50,
    "valence":           1.00,
    "tempo":             0.75,
    "acousticness":      0.50,
    "speechiness":       0.25,
    "instrumentalness":  0.25,
}
MAX_SCORE: float = sum(_POINTS.values())  # 7.75

# BPM normalization range — values outside are clamped, not rejected.
_BPM_MIN: float = 60.0
_BPM_MAX: float = 152.0


def _norm_bpm(bpm: float) -> float:
    """Map raw BPM onto [0, 1], clamping values outside the catalog range."""
    return max(0.0, min(1.0, (bpm - _BPM_MIN) / (_BPM_MAX - _BPM_MIN)))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py

    speechiness and instrumentalness default to 0.05 so that Song objects
    constructed without those fields (e.g. in older tests) remain valid.
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    speechiness: float = 0.05
    instrumentalness: float = 0.05


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py

    Categorical fields (favorite_genre, favorite_mood) are matched exactly.
    Continuous fields (target_*) use proximity scoring:
        feature_score = 1 - |user_target - song_value|

    target_tempo_bpm is raw BPM; _norm_bpm() converts it before comparison.
    Optional depth fields default to neutral mid-range values so callers that
    don't specify them don't accidentally bias the score.
    """
    # Identity
    name: str

    # Categorical (weight: genre 0.28, mood 0.22)
    favorite_genre: str
    favorite_mood: str

    # Core continuous (weight: energy 0.18, valence 0.13, tempo 0.09, acousticness 0.04)
    target_energy: float
    target_valence: float
    target_tempo_bpm: float
    target_acousticness: float

    # Depth features — now active in scoring (weight: 0.03 each)
    target_speechiness: float = 0.05       # 0.0 sung → 1.0 spoken/rapped
    target_instrumentalness: float = 0.05  # 0.0 vocal → 1.0 no vocals

    # Stored but not yet weighted (reserved for ranking diversity logic)
    target_danceability: float = 0.60


# ---------------------------------------------------------------------------
# Functional API  (used by src/main.py)
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """
    Load songs from a CSV file and return a list of plain dicts.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            songs.append({
                "id":               int(row["id"]),
                "title":            row["title"],
                "artist":           row["artist"],
                "genre":            row["genre"],
                "mood":             row["mood"],
                "energy":           float(row["energy"]),
                "tempo_bpm":        float(row["tempo_bpm"]),
                "valence":          float(row["valence"]),
                "danceability":     float(row["danceability"]),
                "acousticness":     float(row["acousticness"]),
                "speechiness":      float(row["speechiness"]),
                "instrumentalness": float(row["instrumentalness"]),
            })
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Score a single song against a user preference dict using the point recipe.

    Returns (score, reasons) where:
      score   — total points earned, between 0.0 and MAX_SCORE (7.75)
      reasons — human-readable explanation of every feature's contribution

    Algorithm Recipe:
      Categorical features (binary — match = full points, no match = 0):
        genre match  → +2.00 pts   (hard taste boundary)
        mood match   → +1.50 pts   (listening intent)

      Continuous features (proximity scoring):
        earned = max_pts × (1 − |user_target − song_value|)
        energy           → up to +1.50 pts
        valence          → up to +1.00 pts
        tempo (normed)   → up to +0.75 pts
        acousticness     → up to +0.50 pts
        speechiness      → up to +0.25 pts
        instrumentalness → up to +0.25 pts

      tempo_bpm is normalized to [0, 1] via _norm_bpm() before comparison.
      A value of 0.0 is as valid as 1.0 — closeness to the user's target earns points.

    Required by recommend_songs() and src/main.py
    """
    score = 0.0
    reasons: List[str] = []

    # --- Categorical features (binary: match = full points, else 0) ---
    if song["genre"] == user_prefs["genre"]:
        score += _POINTS["genre"]
        reasons.append(f"genre match ({song['genre']}) +{_POINTS['genre']:.2f}pts")
    else:
        reasons.append(f"genre mismatch ({song['genre']} ≠ {user_prefs['genre']}) +0.00pts")

    if song["mood"] == user_prefs["mood"]:
        score += _POINTS["mood"]
        reasons.append(f"mood match ({song['mood']}) +{_POINTS['mood']:.2f}pts")
    else:
        reasons.append(f"mood mismatch ({song['mood']} ≠ {user_prefs['mood']}) +0.00pts")

    # --- Continuous features (proximity = 1 − |diff|, scaled by max points) ---
    user_tempo_norm = _norm_bpm(user_prefs["target_tempo_bpm"])
    song_tempo_norm = _norm_bpm(song["tempo_bpm"])

    continuous = [
        ("energy",           user_prefs["target_energy"],                   song["energy"],            _POINTS["energy"]),
        ("valence",          user_prefs["target_valence"],                   song["valence"],           _POINTS["valence"]),
        ("tempo",            user_tempo_norm,                                song_tempo_norm,           _POINTS["tempo"]),
        ("acousticness",     user_prefs["target_acousticness"],              song["acousticness"],      _POINTS["acousticness"]),
        ("speechiness",      user_prefs.get("target_speechiness",    0.05),  song["speechiness"],       _POINTS["speechiness"]),
        ("instrumentalness", user_prefs.get("target_instrumentalness",0.05), song["instrumentalness"],  _POINTS["instrumentalness"]),
    ]

    for name, user_val, song_val, max_pts in continuous:
        proximity = 1.0 - abs(user_val - song_val)
        earned = proximity * max_pts
        score += earned
        reasons.append(
            f"{name}: song={song_val:.2f}, target={user_val:.2f} → +{earned:.2f}pts"
        )

    return round(score, 3), reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Score every song, sort by score descending, return the top k.
    Each item in the returned list is (song_dict, score, explanation).
    Required by src/main.py
    """
    scored = [
        (song, *score_song(user_prefs, song))
        for song in songs
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    # Flatten reasons list into a single explanation string
    return [
        (song, score, "; ".join(reasons) if reasons else "no strong feature matches")
        for song, score, reasons in scored[:k]
    ]


# ---------------------------------------------------------------------------
# OOP API  (used by tests/test_recommender.py)
# ---------------------------------------------------------------------------

def _song_to_dict(song: Song) -> Dict:
    """Convert a Song dataclass into the flat dict expected by score_song()."""
    return {
        "genre":            song.genre,
        "mood":             song.mood,
        "energy":           song.energy,
        "tempo_bpm":        song.tempo_bpm,
        "valence":          song.valence,
        "acousticness":     song.acousticness,
        "speechiness":      song.speechiness,
        "instrumentalness": song.instrumentalness,
    }


def _profile_to_dict(user: UserProfile) -> Dict:
    """Convert a UserProfile dataclass into the flat dict expected by score_song()."""
    return {
        "genre":                  user.favorite_genre,
        "mood":                   user.favorite_mood,
        "target_energy":          user.target_energy,
        "target_valence":         user.target_valence,
        "target_tempo_bpm":       user.target_tempo_bpm,
        "target_acousticness":    user.target_acousticness,
        "target_speechiness":     user.target_speechiness,
        "target_instrumentalness":user.target_instrumentalness,
    }


class Recommender:
    """
    OOP wrapper around the functional scoring pipeline.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k Song objects ranked by score against the given UserProfile."""
        user_dict = _profile_to_dict(user)
        scored = [
            (song, score_song(user_dict, _song_to_dict(song))[0])
            for song in self.songs
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable score breakdown string for a single song."""
        _, reasons = score_song(_profile_to_dict(user), _song_to_dict(song))
        score, _ = score_song(_profile_to_dict(user), _song_to_dict(song))
        body = "; ".join(reasons) if reasons else "no strong feature matches"
        return f"Score {score:.2f}: {body}"
