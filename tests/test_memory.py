from src.memory import MAX_TURNS, add_turn, format_history


def test_add_turn_appends():
    history = add_turn([], "Q1", "SELECT 1", "A1")
    assert history == [{"question": "Q1", "sql": "SELECT 1", "answer": "A1"}]


def test_add_turn_bounds_to_max_turns():
    history: list[dict] = []
    for i in range(MAX_TURNS + 3):
        history = add_turn(history, f"Q{i}", f"SQL{i}", f"A{i}")
    assert len(history) == MAX_TURNS
    assert history[-1]["question"] == f"Q{MAX_TURNS + 2}"
    assert history[0]["question"] == "Q3"  # oldest 3 turns dropped


def test_format_history_empty():
    assert format_history([]) == "No prior conversation."


def test_format_history_includes_turns():
    history = [{"question": "Q1", "sql": "SELECT 1", "answer": "A1"}]
    text = format_history(history)
    assert "Q1" in text
    assert "SELECT 1" in text
    assert "A1" in text
