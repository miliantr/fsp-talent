"""Item analysis used on real attempts (scripts/item_analysis.py)."""

from scripts.item_analysis import analyse


def test_upper_lower_index_separates_good_and_useless_items():
    # 100 candidates with rest scores 0..99: the good item is solved by the stronger half only
    good = analyse([(r, r >= 50) for r in range(100)])
    assert good["d"] == 1.0 and good["verdict"] == "good" and good["r_pb"] > 0.8
    useless = analyse([(r, r % 2 == 0) for r in range(100)])
    assert abs(useless["d"]) < 0.1 and useless["verdict"] == "review"
    assert useless["p"] == 0.5
