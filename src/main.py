"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import textwrap

try:
    from tabulate import tabulate
    _TABULATE_AVAILABLE = True
except ImportError:
    _TABULATE_AVAILABLE = False

from recommender import load_songs, recommend_songs, MAX_SCORE, SCORING_MODES


def print_recommendations(user_prefs: dict, songs: list, mode: str = "balanced") -> None:
    """Print a clean ranked recommendation list for a single profile and scoring mode."""
    weights = SCORING_MODES[mode]
    max_score = sum(weights.values())
    recommendations = recommend_songs(user_prefs, songs, k=5, weights=weights)
    print(f"\n{'='*60}")
    print(f"  Music Recommender — Top 5 for: {user_prefs['name']}")
    print(f"  Taste: {user_prefs['genre']} / {user_prefs['mood']}")
    print(f"  Mode:  {mode}")
    print(f"{'='*60}\n")
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"#{rank}  {song['title']}  —  {song['artist']}")
        print(f"    Score: {score:.2f} / {max_score:.2f}")
        print(f"    Why:")
        for reason in explanation.split("; "):
            print(f"      • {reason}")
        print()


def _wrap(text: str, width: int = 45) -> str:
    """Wrap a semicolon-delimited reason string into newline-separated lines."""
    lines = []
    for reason in text.split("; "):
        lines.extend(textwrap.wrap(reason, width))
    return "\n".join(lines)


def print_recommendation_table(user_prefs: dict, songs: list, mode: str = "balanced") -> None:
    """Print top-5 recommendations as a formatted table with per-feature score reasons.

    Uses tabulate (grid format) when available; falls back to plain ASCII boxes.
    Columns: Rank | Title | Artist | Genre | Score | Reasons
    """
    weights = SCORING_MODES[mode]
    max_score = sum(weights.values())
    recommendations = recommend_songs(user_prefs, songs, k=5, weights=weights)

    print(f"\n{'#'*72}")
    print(f"  TABLE VIEW — Top 5 for: {user_prefs['name']}  |  mode: {mode}")
    print(f"{'#'*72}")

    headers = ["#", "Title", "Artist", "Genre", "Score", "Reasons"]
    rows = []
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        rows.append([
            rank,
            song["title"],
            song["artist"],
            song["genre"],
            f"{score:.2f}\n/{max_score:.2f}",
            _wrap(explanation),
        ])

    if _TABULATE_AVAILABLE:
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        # Fallback: simple fixed-width ASCII table
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                cell_width = max(len(line) for line in str(cell).split("\n"))
                col_widths[i] = max(col_widths[i], cell_width)

        def _divider():
            return "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

        def _row_str(cells):
            # Split each cell into lines, pad to same height
            split = [str(c).split("\n") for c in cells]
            height = max(len(s) for s in split)
            padded = [s + [""] * (height - len(s)) for s in split]
            lines = []
            for i in range(height):
                lines.append(
                    "|" + "|".join(f" {padded[j][i]:<{col_widths[j]}} " for j in range(len(cells))) + "|"
                )
            return "\n".join(lines)

        print(_divider())
        print(_row_str(headers))
        print(_divider().replace("-", "="))
        for row in rows:
            print(_row_str(row))
            print(_divider())
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    # ---------------------------------------------------------------
    # Standard profiles
    # ---------------------------------------------------------------

    # Profile A — Late-night lo-fi study session
    late_night_studier = {
        "name": "Late-Night Studier",
        "genre": "lofi",
        "mood": "focused",
        "target_energy": 0.38,
        "target_valence": 0.58,
        "target_tempo_bpm": 76,
        "target_acousticness": 0.82,
        "target_speechiness": 0.03,
        "target_instrumentalness": 0.88,
    }

    # Profile B — High-energy pop workout
    morning_runner = {
        "name": "High-Energy Pop",
        "genre": "pop",
        "mood": "intense",
        "target_energy": 0.92,
        "target_valence": 0.80,
        "target_tempo_bpm": 132,
        "target_acousticness": 0.06,
        "target_speechiness": 0.07,
        "target_instrumentalness": 0.02,
    }

    # Profile C — Deep, slow, melancholic folk
    sunday_wind_down = {
        "name": "Sunday Wind-Down",
        "genre": "folk",
        "mood": "melancholic",
        "target_energy": 0.32,
        "target_valence": 0.36,
        "target_tempo_bpm": 70,
        "target_acousticness": 0.90,
        "target_speechiness": 0.07,
        "target_instrumentalness": 0.12,
    }

    # ---------------------------------------------------------------
    # Adversarial / edge-case profiles
    # Designed to probe weaknesses in the scoring logic.
    # ---------------------------------------------------------------

    # Edge case 1 — Contradictory mood vs. energy
    # High energy (0.92) but wants a "sad" mood.
    # No song in the catalog is both high-energy AND sad — the system
    # must choose: reward energy proximity or the mood label?
    # Expected: sad songs (blues) may rank high on mood but lose on energy;
    # high-energy songs win on energy but miss the mood bonus entirely.
    contradictory = {
        "name": "Contradictory (High-Energy + Sad)",
        "genre": "blues",
        "mood": "sad",
        "target_energy": 0.92,          # wants intense energy…
        "target_valence": 0.15,         # …but very dark emotional tone
        "target_tempo_bpm": 130,        # fast pace
        "target_acousticness": 0.50,    # neutral texture
        "target_speechiness": 0.08,
        "target_instrumentalness": 0.10,
    }

    # Edge case 2 — Ghost genre (no catalog match)
    # "classical/aggressive" does not exist in the catalog.
    # Every song will score 0 on genre AND mood, so ranking falls
    # entirely to the continuous features — reveals the "floor" behavior.
    ghost_profile = {
        "name": "Ghost Profile (classical + aggressive)",
        "genre": "classical",
        "mood": "aggressive",
        "target_energy": 0.95,
        "target_valence": 0.20,
        "target_tempo_bpm": 160,
        "target_acousticness": 0.80,    # unusual: wants acoustic AND aggressive
        "target_speechiness": 0.05,
        "target_instrumentalness": 0.90,
    }

    # Edge case 3 — All-neutral (mid-point everything)
    # Every continuous target is 0.5, genre/mood are rare in the catalog.
    # Tests whether the system produces a meaningful ranking or a near-tie
    # when all features score equally mediocre.
    all_neutral = {
        "name": "All-Neutral (mid-point everything)",
        "genre": "r&b",
        "mood": "romantic",
        "target_energy": 0.50,
        "target_valence": 0.50,
        "target_tempo_bpm": 106,        # midpoint of 60–152 BPM range
        "target_acousticness": 0.50,
        "target_speechiness": 0.50,
        "target_instrumentalness": 0.50,
    }

    # ---------------------------------------------------------------
    # Run all profiles — balanced mode
    # ---------------------------------------------------------------
    all_profiles = [
        late_night_studier,
        morning_runner,
        sunday_wind_down,
        contradictory,
        ghost_profile,
        all_neutral,
    ]

    for profile in all_profiles:
        print_recommendations(profile, songs, mode="balanced")

    # ---------------------------------------------------------------
    # Scoring mode comparison — run one profile through all 4 modes
    # to show how the strategy changes the ranking.
    # ---------------------------------------------------------------
    print("\n" + "#" * 60)
    print("  SCORING MODE COMPARISON — High-Energy Pop profile")
    print("#" * 60)
    for mode in SCORING_MODES:
        print_recommendations(morning_runner, songs, mode=mode)

    # ---------------------------------------------------------------
    # Visual summary tables — one per profile, balanced mode
    # ---------------------------------------------------------------
    print("\n" + "#" * 72)
    print("  VISUAL SUMMARY TABLES")
    print("#" * 72)
    for profile in all_profiles:
        print_recommendation_table(profile, songs, mode="balanced")

    # ---------------------------------------------------------------
    # Diversity penalty demo
    # ---------------------------------------------------------------
    print_diversity_comparison(late_night_studier, songs)
    print_diversity_comparison(morning_runner, songs)


def print_diversity_comparison(user_prefs: dict, songs: list) -> None:
    """Show top-5 with and without diversity penalty side by side."""
    weights = SCORING_MODES["balanced"]
    max_score = sum(weights.values())

    plain = recommend_songs(user_prefs, songs, k=5, weights=weights)
    diverse = recommend_songs(
        user_prefs, songs, k=5, weights=weights,
        artist_penalty=1.0, genre_penalty=0.5,
    )

    print(f"\n{'#'*60}")
    print(f"  DIVERSITY PENALTY DEMO — {user_prefs['name']}")
    print(f"  artist_penalty=1.00  genre_penalty=0.50")
    print(f"{'#'*60}")

    print(f"\n{'─'*28}  WITHOUT  {'─'*28}")
    for rank, (song, score, _) in enumerate(plain, 1):
        print(f"  #{rank}  {song['title']:<30} {song['artist']:<18} "
              f"[{song['genre']}]  {score:.2f}/{max_score:.2f}")

    print(f"\n{'─'*28}   WITH     {'─'*28}")
    for rank, (song, score, explanation) in enumerate(diverse, 1):
        penalty_flag = " ★" if "repeat" in explanation else ""
        print(f"  #{rank}  {song['title']:<30} {song['artist']:<18} "
              f"[{song['genre']}]  {score:.2f}/{max_score:.2f}{penalty_flag}")
    print()


if __name__ == "__main__":
    main()
