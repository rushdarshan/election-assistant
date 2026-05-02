"""Property-based tests for quiz grading and scoring."""

import pytest
from hypothesis import given, strategies as st
from app.quiz import grade_quiz, calculate_knowledge_score
from app.models import QuizSession
from tests.strategies import quiz_grading_inputs

class TestQuizGrading:
    """Properties of grade_quiz."""

    @pytest.mark.asyncio
    @given(inputs=quiz_grading_inputs())
    async def test_grade_quiz_contract(self, inputs):
        """Assert score is correct and breakdown matches input questions."""
        session = QuizSession(country="US", state="CA")
        result = await grade_quiz(session, inputs["attempts"], inputs["questions"])
        
        assert result.total == len(inputs["questions"])
        assert 0 <= result.score <= result.total
        assert 0.0 <= result.percentage <= 100.0
        
        # Verify score manually
        expected_score = sum(1 for a, q in zip(inputs["attempts"], inputs["questions"]) 
                             if a.selected_idx == q.correct_answer_idx)
        assert result.score == expected_score
        
        # Verify breakdown
        for q in inputs["questions"]:
            assert q.category in result.category_breakdown
            assert result.category_breakdown[q.category]["total"] >= 1

class TestKnowledgeScore:
    """Properties of calculate_knowledge_score."""

    @given(
        total_quizzes=st.integers(min_value=0, max_value=100),
        best_score=st.floats(min_value=0, max_value=100),
        questions_asked=st.integers(min_value=0, max_value=100)
    )
    @pytest.mark.asyncio
    async def test_knowledge_score_range(self, total_quizzes, best_score, questions_asked):
        """Assert knowledge score is always within 0-100."""
        score = await calculate_knowledge_score(total_quizzes, best_score, questions_asked)
        assert 0.0 <= score <= 100.0

    @given(
        total_quizzes=st.integers(min_value=1, max_value=100),
        best_score=st.floats(min_value=0, max_value=100),
        questions_asked=st.integers(min_value=0, max_value=100)
    )
    @pytest.mark.asyncio
    async def test_knowledge_score_monotonicity(self, total_quizzes, best_score, questions_asked):
        """Assert score increases with better inputs."""
        score_base = await calculate_knowledge_score(total_quizzes, best_score, questions_asked)
        
        # Better quiz score
        if best_score < 100:
            score_better = await calculate_knowledge_score(total_quizzes, best_score + 1, questions_asked)
            assert score_better >= score_base
            
        # More questions asked (up to 10)
        if questions_asked < 10:
            score_more_q = await calculate_knowledge_score(total_quizzes, best_score, questions_asked + 1)
            assert score_more_q >= score_base
