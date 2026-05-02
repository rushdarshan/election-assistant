"""Property-based tests for DeadlineValidator."""

import pytest
from hypothesis import given
from app.validators.deadline_validator import DeadlineValidator
from tests.strategies import deadline_validator_inputs

class TestDeadlineValidator:
    """Properties of DeadlineValidator.validate."""

    @given(inputs=deadline_validator_inputs())
    def test_confidence_values(self, inputs):
        """Assert confidence is one of the expected semantic levels."""
        validator = DeadlineValidator(inputs["anchor_dates"])
        result = validator.validate(
            state=inputs["state"],
            api_date=inputs["api_date"],
            deadline_type=inputs["deadline_type"]
        )
        
        assert result.confidence in ["verified", "api_data", "conflict", "manual", "low"]

    @given(inputs=deadline_validator_inputs())
    def test_verified_contract(self, inputs):
        """If api_date and manual match, confidence MUST be verified."""
        manual_result = inputs["anchor_dates"].get(inputs["deadline_type"])
        
        if inputs["api_date"] and manual_result and inputs["api_date"] == manual_result:
            validator = DeadlineValidator(inputs["anchor_dates"])
            result = validator.validate(
                state=inputs["state"],
                api_date=inputs["api_date"],
                deadline_type=inputs["deadline_type"]
            )
            assert result.confidence == "verified"
            assert result.date == inputs["api_date"]
            assert "google" in result.sources
            assert "manual" in result.sources

    @given(inputs=deadline_validator_inputs())
    def test_conflict_contract(self, inputs):
        """If api_date and manual conflict, date MUST be None and confidence conflict."""
        manual_result = inputs["anchor_dates"].get(inputs["deadline_type"])
        
        if inputs["api_date"] and manual_result and inputs["api_date"] != manual_result:
            validator = DeadlineValidator(inputs["anchor_dates"])
            result = validator.validate(
                state=inputs["state"],
                api_date=inputs["api_date"],
                deadline_type=inputs["deadline_type"]
            )
            assert result.confidence == "conflict"
            assert result.date is None
            assert result.error is not None

    @given(inputs=deadline_validator_inputs())
    def test_no_crash(self, inputs):
        """Smoke test: validator should never crash for valid inputs."""
        validator = DeadlineValidator(inputs["anchor_dates"])
        validator.validate(
            state=inputs["state"],
            api_date=inputs["api_date"],
            deadline_type=inputs["deadline_type"]
        )
