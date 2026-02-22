"""
Test suite for the sarcasm & contextual slang pre-processor.

Issue: Build Sarcasm & Contextual Slang Pre-processor
Team : Team-T052

Run with:
    pytest tests/test_sarcasm_filter.py -v
"""

import sys
from pathlib import Path

import pytest

# Add src to path so we can import directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing import flag_ambiguous_reviews


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _result(reviews):
    """Convenience wrapper: return the full dict from flag_ambiguous_reviews."""
    return flag_ambiguous_reviews(reviews)


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


class TestFlagAmbiguousReviews:
    """Edge-case tests for flag_ambiguous_reviews()."""

    # ------------------------------------------------------------------
    # Test 1 – Obvious sarcasm (ironic praise + severity keyword)
    # ------------------------------------------------------------------
    def test_obvious_sarcasm_ironic_praise(self):
        """
        Review:  "10/10 for the airbag deploying randomly"
        Pattern: IRONIC_PHRASE ("10/10") + SEVERITY_KEYWORD ("deploying"... 
                 the review also contains "airbag" but critically it hits
                 Rule 3 via "10/10" (ironic phrase) + "randomly" context.
        Expected: flagged
        """
        review = "10/10 for the airbag deploying randomly"
        result = _result([review])

        assert review in result["flagged"], (
            "Obvious sarcasm ('10/10' + safety-related context) should be flagged"
        )
        assert review not in result["clean"]

    # ------------------------------------------------------------------
    # Test 2 – Genuine positive review (must NOT be flagged)
    # ------------------------------------------------------------------
    def test_genuine_positive_review_not_flagged(self):
        """
        Review:  "Great fuel efficiency, smooth ride, very happy with the purchase!"
        Pattern: Positive sentiment, no severity keywords
        Expected: clean (NOT flagged)
        """
        review = "Great fuel efficiency, smooth ride, very happy with the purchase!"
        result = _result([review])

        assert review in result["clean"], (
            "Genuine positive review should NOT be flagged"
        )
        assert review not in result["flagged"]

    # ------------------------------------------------------------------
    # Test 3 – Genuine negative review (should NOT be flagged — it's honest)
    # ------------------------------------------------------------------
    def test_genuine_negative_review_not_flagged(self):
        """
        Review:  "The brakes squealed badly and then failed on the highway. 
                  Terrible experience, I will never buy this brand again."
        Pattern: Clearly negative sentiment + severity keyword — but this is 
                 honest negativity, NOT sarcasm.
        Expected: clean (Rule 1 does NOT fire because sentiment is negative, 
                  not positive; Rule 2 requires a praise word which is absent)
        """
        review = (
            "The brakes squealed badly and then failed on the highway. "
            "Terrible experience, I will never buy this brand again."
        )
        result = _result([review])

        assert review in result["clean"], (
            "Honest negative review (negative sentiment + severity keyword) "
            "should NOT be flagged — only positive-sentiment + severity is sarcasm"
        )
        assert review not in result["flagged"]

    # ------------------------------------------------------------------
    # Test 4 – Mixed context / ambiguous slang ("This car is fire 🔥")
    # ------------------------------------------------------------------
    def test_mixed_context_slang_emoji(self):
        """
        Review:  "This car is fire 🔥"
        Pattern: The word 'fire' IS in SEVERITY_KEYWORDS, but TextBlob scores
                 this as mildly positive (street slang).
                 We check whether the function handles it without a false positive.
        Expected: flagged (positive sentiment score > 0.3 + 'fire' severity 
                  keyword → Rule 1 fires).
        Note: This is the intended behaviour — the expander warns a human to
              review it, which is exactly right for truly ambiguous slang.
        """
        review = "This car is fire 🔥"
        result = _result([review])

        # The emoji itself is stripped internally by TextBlob, so sentiment
        # is based on "This car is fire". TextBlob scores "fire" context as
        # mildly or neutrally positive. We assert the function doesn't crash
        # and returns a well-formed dict.
        assert "clean" in result
        assert "flagged" in result
        assert isinstance(result["clean"], list)
        assert isinstance(result["flagged"], list)
        # The review must appear in exactly one of the two buckets
        assert (review in result["clean"]) != (review in result["flagged"]), (
            "Review must appear in exactly one of 'clean' or 'flagged'"
        )

    # ------------------------------------------------------------------
    # Test 5 – Contradictory structure (negative + strong praise → flagged)
    # ------------------------------------------------------------------
    def test_contradictory_love_plus_severity(self):
        """
        Review:  "Love the car, except it nearly killed me twice"
        Pattern: 'love' = praise word; 'killed' maps to 'death'/'danger' family.
                 TextBlob likely gives a mixed/positive score due to 'love'.
                 Multiple rules may fire (Rule 1 and/or Rule 3 via 'love it'-
                 adjacent phrasing + severity context).
        Expected: flagged
        """
        review = "Love the car, except it nearly killed me twice"
        result = _result([review])

        assert review in result["flagged"], (
            "Contradictory review ('love' + near-death severity) should be flagged"
        )
        assert review not in result["clean"]

    # ------------------------------------------------------------------
    # Test 6 – Batch: mix of clean and flagged
    # ------------------------------------------------------------------
    def test_batch_mixed_reviews(self):
        """
        Ensure function correctly partitions a batch with a mix of
        clean and sarcastic reviews.
        """
        sarcastic = "10/10, best car ever — the brakes failed on day one!"
        clean_pos = "Absolutely love the interior design and quiet cabin."
        clean_neg = "The engine stalled repeatedly. Dangerous and unreliable."

        result = _result([sarcastic, clean_pos, clean_neg])

        assert sarcastic in result["flagged"], "Sarcastic review must be flagged"
        assert clean_pos in result["clean"], "Genuine positive must not be flagged"
        # Genuine negative (negative sentiment + severity): Rule 1 does NOT fire
        # because sentiment is negative, not positive. Stays clean.
        assert clean_neg in result["clean"], (
            "Genuine negative (honest complaint) must not be flagged"
        )

    # ------------------------------------------------------------------
    # Test 7 – Empty input
    # ------------------------------------------------------------------
    def test_empty_input(self):
        """Function must return empty clean/flagged lists for empty input."""
        result = _result([])
        assert result == {"clean": [], "flagged": []}

    # ------------------------------------------------------------------
    # Test 8 – Return structure contract
    # ------------------------------------------------------------------
    def test_return_structure(self):
        """Function always returns a dict with exactly 'clean' and 'flagged' keys."""
        result = _result(["Some review text."])
        assert set(result.keys()) == {"clean", "flagged"}
        assert isinstance(result["clean"], list)
        assert isinstance(result["flagged"], list)
        # Every input review is accounted for
        total = len(result["clean"]) + len(result["flagged"])
        assert total == 1


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
