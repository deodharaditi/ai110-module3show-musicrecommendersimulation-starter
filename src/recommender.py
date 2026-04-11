import csv
from dataclasses import dataclass
from typing import List, Dict, Tuple

# ---------------------------------------------------------------------------
# Algorithm Recipe — point budget
# ---------------------------------------------------------------------------
#
# Each feature contributes a maximum number of points toward a song's total.
# The maximum possible score is 9.50 points (a perfect match on every feature).
#
# Categorical features (binary match):
#   Genre  +2.00  — hard taste boundary; mismatches are near-automatic rejections
#   Mood   +1.50  — strong intent signal; a correct mood can tip a close genre contest
#
# Continuous features (proximity scoring):
#   points = max_points × (1 − |user_target − song_value|)
#   A score of 1.0 is as valid as 0.0 — closeness is what matters, not magnitude.
#
#   Energy          up to +1.50  — most powerful vibe signal
#   Valence         up to +1.00  — emotional tone: dark vs bright
#   Tempo           up to +0.75  — activity context: running pace vs study pace
#   Acousticness    up to +0.50  — texture: organic vs electronic
#   Speechiness     up to +0.25  — vocal density: sung vs rapped vs instrumental
#   Instrumentalness up to +0.25 — no-vocals preference; pairs with speechiness
#   Popularity      up to +0.50  — how well-known the song is
#   Release decade  up to +0.50  — era preference (1970→0.0 … 2020→1.0)
#   Liveness        up to +0.25  — studio vs concert-like feel
#   Loudness        up to +0.25  — quiet vs loud production
#
# Binary features (match = full points, mismatch = 0):
#   Explicit        up to +0.25  — explicit content preference
#
# Max total: 7.75 + 1.75 = 9.50 pts
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
    "popularity":        0.50,
    "release_decade":    0.50,
    "liveness":          0.25,
    "loudness":          0.25,
    "explicit":          0.25,
}
MAX_SCORE: float = sum(_POINTS.values())  # 9.50

# ---------------------------------------------------------------------------
# Scoring modes — Strategy pattern via plain dicts
# ---------------------------------------------------------------------------
# Each mode is a complete weight table that replaces _POINTS for one run.
# score_song() and recommend_songs() accept an optional `weights` argument;
# when omitted they fall back to _POINTS (the balanced default).
#
# Design rationale: because score_song() already reads weights by key name
# (e.g. _POINTS["genre"]) rather than hardcoding numbers, swapping the dict
# is all that is needed to change the strategy — no subclasses, no flags.
# ---------------------------------------------------------------------------

# Mode 1 — Genre-First: genre is the dominant signal, everything else secondary.
# Use when: user has a hard genre boundary and wants no surprises.
SCORING_GENRE_FIRST: Dict[str, float] = {
    "genre":             4.00,   # doubled — genre match is near-mandatory
    "mood":              1.50,
    "energy":            0.75,   # halved — vibe matters less than genre label
    "valence":           0.50,
    "tempo":             0.40,
    "acousticness":      0.25,
    "speechiness":       0.15,
    "instrumentalness":  0.15,
    "popularity":        0.25,
    "release_decade":    0.25,
    "liveness":          0.10,
    "loudness":          0.10,
    "explicit":          0.15,
}

# Mode 2 — Vibe-First (energy + valence lead): genre is soft, sound feel dominates.
# Use when: user wants a specific energy/emotional tone regardless of genre label.
SCORING_VIBE_FIRST: Dict[str, float] = {
    "genre":             0.50,   # soft — wrong genre is only a small penalty
    "mood":              1.00,
    "energy":            3.50,   # energy is the primary signal
    "valence":           2.50,   # emotional tone close second
    "tempo":             1.00,
    "acousticness":      0.75,
    "speechiness":       0.25,
    "instrumentalness":  0.25,
    "popularity":        0.25,
    "release_decade":    0.25,
    "liveness":          0.15,
    "loudness":          0.30,
    "explicit":          0.10,
}

# Mode 3 — Discovery: de-emphasizes popularity so deep cuts surface.
# Use when: user is tired of the same well-known songs and wants hidden gems.
SCORING_DISCOVERY: Dict[str, float] = {
    "genre":             2.00,
    "mood":              1.50,
    "energy":            1.50,
    "valence":           1.00,
    "tempo":             0.75,
    "acousticness":      0.50,
    "speechiness":       0.25,
    "instrumentalness":  0.25,
    "popularity":        -0.30,  # negative: penalizes well-known songs
    "release_decade":    0.75,   # bonus for older eras — surfacing vintage tracks
    "liveness":          0.25,
    "loudness":          0.25,
    "explicit":          0.25,
}

# Registry — maps string names to weight dicts for easy lookup in main.py
SCORING_MODES: Dict[str, Dict[str, float]] = {
    "balanced":    _POINTS,
    "genre_first": SCORING_GENRE_FIRST,
    "vibe_first":  SCORING_VIBE_FIRST,
    "discovery":   SCORING_DISCOVERY,
}

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
    popularity: int = 50
    release_decade: int = 2010
    liveness: float = 0.10
    loudness_norm: float = 0.50
    explicit: int = 0


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

    # New depth features
    target_popularity: int = 50
    target_release_decade: int = 2010
    target_liveness: float = 0.10
    target_loudness: float = 0.50
    prefers_explicit: int = 0


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
                "popularity":       int(row["popularity"]),
                "release_decade":   int(row["release_decade"]),
                "liveness":         float(row["liveness"]),
                "loudness_norm":    float(row["loudness_norm"]),
                "explicit":         int(row["explicit"]),
            })
    return songs


def score_song(
    user_prefs: Dict,
    song: Dict,
    weights: Dict[str, float] = None,
) -> Tuple[float, List[str]]:
    """Score a single song using the given weight table (defaults to _POINTS)."""
    w = weights if weights is not None else _POINTS
    score = 0.0
    reasons: List[str] = []

    # --- Categorical features (binary: match = full points, else 0) ---
    if song["genre"] == user_prefs["genre"]:
        score += w["genre"]
        reasons.append(f"genre match ({song['genre']}) +{w['genre']:.2f}pts")
    else:
        reasons.append(f"genre mismatch ({song['genre']} ≠ {user_prefs['genre']}) +0.00pts")

    if song["mood"] == user_prefs["mood"]:
        score += w["mood"]
        reasons.append(f"mood match ({song['mood']}) +{w['mood']:.2f}pts")
    else:
        reasons.append(f"mood mismatch ({song['mood']} ≠ {user_prefs['mood']}) +0.00pts")

    # --- Continuous features (proximity = 1 − |diff|, scaled by max points) ---
    user_tempo_norm = _norm_bpm(user_prefs["target_tempo_bpm"])
    song_tempo_norm = _norm_bpm(song["tempo_bpm"])

    continuous = [
        ("energy",           user_prefs["target_energy"],                   song["energy"],            w["energy"]),
        ("valence",          user_prefs["target_valence"],                   song["valence"],           w["valence"]),
        ("tempo",            user_tempo_norm,                                song_tempo_norm,           w["tempo"]),
        ("acousticness",     user_prefs["target_acousticness"],              song["acousticness"],      w["acousticness"]),
        ("speechiness",      user_prefs.get("target_speechiness",    0.05),  song["speechiness"],       w["speechiness"]),
        ("instrumentalness", user_prefs.get("target_instrumentalness",0.05), song["instrumentalness"],  w["instrumentalness"]),
        ("popularity",       user_prefs.get("target_popularity",     50) / 100,
                             song.get("popularity", 50) / 100,              w["popularity"]),
        ("release_decade",   (user_prefs.get("target_release_decade", 2010) - 1970) / 50,
                             (song.get("release_decade", 2010) - 1970) / 50, w["release_decade"]),
        ("liveness",         user_prefs.get("target_liveness",       0.10),  song.get("liveness",       0.10), w["liveness"]),
        ("loudness",         user_prefs.get("target_loudness",       0.50),  song.get("loudness_norm",  0.50), w["loudness"]),
    ]

    for name, user_val, song_val, max_pts in continuous:
        proximity = 1.0 - abs(user_val - song_val)
        earned = proximity * max_pts
        score += earned
        reasons.append(
            f"{name}: song={song_val:.2f}, target={user_val:.2f} → +{earned:.2f}pts"
        )

    # --- Explicit content (binary match) ---
    song_explicit = song.get("explicit", 0)
    user_explicit = user_prefs.get("prefers_explicit", 0)
    if song_explicit == user_explicit:
        score += w["explicit"]
        reasons.append(f"explicit match ({song_explicit}) +{w['explicit']:.2f}pts")
    else:
        reasons.append(
            f"explicit mismatch (song={song_explicit}, prefers={user_explicit}) +0.00pts"
        )

    return round(score, 3), reasons


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    weights: Dict[str, float] = None,
    artist_penalty: float = 0.0,
    genre_penalty: float = 0.0,
) -> List[Tuple[Dict, float, str]]:
    """Score every song with the given weights, apply diversity penalties, return top k.

    Diversity penalty (greedy re-ranking):
      At each selection step, subtract `artist_penalty` from any candidate whose
      artist already appears in the selected list, and subtract `genre_penalty`
      from any candidate whose genre already appears. The candidate with the
      highest adjusted score is chosen, then added to the seen sets.
      Set both penalties to 0.0 (default) to disable and use plain score ranking.
    """
    scored = [
        (song, *score_song(user_prefs, song, weights))
        for song in songs
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    if artist_penalty == 0.0 and genre_penalty == 0.0:
        return [
            (song, score, "; ".join(reasons) if reasons else "no strong feature matches")
            for song, score, reasons in scored[:k]
        ]

    # Greedy MMR-style diversity selection
    selected: List[Tuple[Dict, float, str]] = []
    seen_artists: set = set()
    seen_genres: set = set()
    remaining = list(scored)

    while len(selected) < k and remaining:
        # Re-score remaining candidates with current penalties
        adjusted = []
        for song, base_score, reasons in remaining:
            penalty = 0.0
            penalty_parts = list(reasons)
            if song["artist"] in seen_artists:
                penalty += artist_penalty
                penalty_parts.append(
                    f"artist repeat ({song['artist']}) -{artist_penalty:.2f}pts"
                )
            if song["genre"] in seen_genres:
                penalty += genre_penalty
                penalty_parts.append(
                    f"genre repeat ({song['genre']}) -{genre_penalty:.2f}pts"
                )
            adjusted.append((song, base_score - penalty, penalty_parts))

        adjusted.sort(key=lambda x: x[1], reverse=True)
        best_song, best_score, best_reasons = adjusted[0]
        selected.append((
            best_song,
            best_score,
            "; ".join(best_reasons) if best_reasons else "no strong feature matches",
        ))
        seen_artists.add(best_song["artist"])
        seen_genres.add(best_song["genre"])
        remaining = [(s, sc, r) for s, sc, r in remaining if s["id"] != best_song["id"]]

    return selected


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
        "popularity":       song.popularity,
        "release_decade":   song.release_decade,
        "liveness":         song.liveness,
        "loudness_norm":    song.loudness_norm,
        "explicit":         song.explicit,
    }


def _profile_to_dict(user: UserProfile) -> Dict:
    """Convert a UserProfile dataclass into the flat dict expected by score_song()."""
    return {
        "genre":                   user.favorite_genre,
        "mood":                    user.favorite_mood,
        "target_energy":           user.target_energy,
        "target_valence":          user.target_valence,
        "target_tempo_bpm":        user.target_tempo_bpm,
        "target_acousticness":     user.target_acousticness,
        "target_speechiness":      user.target_speechiness,
        "target_instrumentalness": user.target_instrumentalness,
        "target_popularity":       user.target_popularity,
        "target_release_decade":   user.target_release_decade,
        "target_liveness":         user.target_liveness,
        "target_loudness":         user.target_loudness,
        "prefers_explicit":        user.prefers_explicit,
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
