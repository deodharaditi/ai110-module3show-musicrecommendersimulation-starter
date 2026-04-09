from src.recommender import Song, UserProfile, Recommender


def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
            # speechiness and instrumentalness use defaults (0.05)
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        name="Test User",
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        target_valence=0.8,
        target_tempo_bpm=120,
        target_acousticness=0.2,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # The pop/happy/high-energy song should rank first.
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        name="Test User",
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        target_valence=0.8,
        target_tempo_bpm=120,
        target_acousticness=0.2,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_genre_mismatch_lowers_score():
    """A wrong genre should produce a noticeably lower score than a match."""
    from src.recommender import score_song, MAX_SCORE

    user = {
        "genre": "lofi",
        "mood": "chill",
        "target_energy": 0.4,
        "target_valence": 0.6,
        "target_tempo_bpm": 80,
        "target_acousticness": 0.8,
        "target_speechiness": 0.04,
        "target_instrumentalness": 0.85,
    }
    lofi_song = {
        "genre": "lofi", "mood": "chill",
        "energy": 0.42, "tempo_bpm": 78, "valence": 0.56,
        "acousticness": 0.71, "speechiness": 0.04, "instrumentalness": 0.85,
    }
    rock_song = {
        "genre": "rock", "mood": "intense",
        "energy": 0.91, "tempo_bpm": 152, "valence": 0.48,
        "acousticness": 0.10, "speechiness": 0.06, "instrumentalness": 0.03,
    }
    lofi_score, _ = score_song(user, lofi_song)
    rock_score, _ = score_song(user, rock_song)

    assert lofi_score > rock_score, (
        f"Expected lofi ({lofi_score}) to outscore rock ({rock_score})"
    )
    # Gap should be at least genre(2.0) + mood(1.5) = 3.5 pts since lofi wins both
    assert lofi_score - rock_score >= 3.5, (
        f"Expected gap >= 3.5 pts, got {lofi_score - rock_score:.3f}"
    )
    # Both scores must stay within the valid point range
    assert 0.0 <= lofi_score <= MAX_SCORE
    assert 0.0 <= rock_score <= MAX_SCORE


def test_tempo_clamping_does_not_crash():
    """BPM values outside 60–152 must clamp cleanly, not produce out-of-range scores."""
    from src.recommender import score_song, MAX_SCORE

    user = {
        "genre": "metal", "mood": "aggressive",
        "target_energy": 0.97, "target_valence": 0.23,
        "target_tempo_bpm": 168,   # above catalog max — should clamp to 1.0
        "target_acousticness": 0.06,
        "target_speechiness": 0.08,
        "target_instrumentalness": 0.12,
    }
    song = {
        "genre": "metal", "mood": "aggressive",
        "energy": 0.97, "tempo_bpm": 168,
        "valence": 0.23, "acousticness": 0.06,
        "speechiness": 0.08, "instrumentalness": 0.12,
    }
    score, _ = score_song(user, song)
    assert 0.0 <= score <= MAX_SCORE, f"Score out of range: {score} (max {MAX_SCORE})"
