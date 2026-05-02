"""Property-based tests for readiness scoring."""

import pytest
from hypothesis import given, settings
from app.readiness import calculate_readiness_score
from app.models import ReadinessProgress
from tests.strategies import readiness_progress_strategy

class TestCalculateReadinessScore:
    """Properties of calculate_readiness_score."""

    @pytest.mark.asyncio
    @given(progress=readiness_progress_strategy)
    async def test_score_ranges(self, progress):
        """Assert all scores are within 0-100 range."""
        score = await calculate_readiness_score(progress)
        
        assert 0.0 <= score.overall_score <= 100.0
        assert 0.0 <= score.registration_ready <= 100.0
        assert 0.0 <= score.voting_ready <= 100.0
        assert 0.0 <= score.knowledge_ready <= 100.0
        assert 0.0 <= score.completion_percentage <= 100.0

    @pytest.mark.asyncio
    @given(progress=readiness_progress_strategy)
    async def test_registration_mapping(self, progress):
        """Assert registration status maps correctly to score."""
        score = await calculate_readiness_score(progress)
        
        if progress.registration_status == "yes":
            assert score.registration_ready == 100.0
        elif progress.registration_status == "no":
            assert score.registration_ready == 50.0
        elif progress.registration_status == "unsure":
            assert score.registration_ready == 25.0
        elif progress.registration_status is None:
            assert score.registration_ready == 0.0

    @pytest.mark.asyncio
    @given(progress=readiness_progress_strategy)
    async def test_checklist_monotonicity(self, progress):
        """Assert score increases (or stays same) as checklist items are completed."""
        score_low = await calculate_readiness_score(progress)
        
        # Increment checklist items
        progress_high = progress.model_copy(update={"checklist_items_completed": progress.checklist_items_completed + 1})
        score_high = await calculate_readiness_score(progress_high)
        
        # Note: checklist_completion is capped at (progress.checklist_items_completed / 8) * 100
        # If it's already at 8 or more, it might continue increasing beyond 100 in the current implementation?
        # Let's check the implementation: checklist_completion = (progress.checklist_items_completed / 8) * 100
        # It's NOT capped in the code, but overall_score is a weighted average.
        
        assert score_high.overall_score >= score_low.overall_score

    @pytest.mark.asyncio
    @given(progress=readiness_progress_strategy)
    async def test_next_steps_not_empty(self, progress):
        """Assert there's always at least one next step or a success message."""
        score = await calculate_readiness_score(progress)
        assert len(score.next_steps) > 0
