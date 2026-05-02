"""Tests for the Scenario Simulator feature."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.scenarios import SCENARIOS, generate_scenario_solution
from app.models import ScenarioResult


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestScenariosPage:
    def test_get_scenarios_returns_200(self, client):
        response = client.get("/scenarios")
        assert response.status_code == 200

    def test_get_scenarios_contains_all_scenario_titles(self, client):
        response = client.get("/scenarios")
        for sid, scenario in SCENARIOS.items():
            assert scenario["title"] in response.text

    def test_get_scenarios_contains_scenario_icons(self, client):
        response = client.get("/scenarios")
        for sid, scenario in SCENARIOS.items():
            assert scenario["icon"] in response.text

    def test_get_scenarios_has_correct_nav_state(self, client):
        response = client.get("/scenarios")
        assert 'aria-current="page"' in response.text


class TestScenarioPartial:
    def test_partial_valid_scenario_returns_html(self, client):
        response = client.post("/scenarios/partial", data={"scenario_id": "lost_voter_id"})
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_partial_all_scenario_ids_accepted(self, client):
        for sid in SCENARIOS:
            response = client.post("/scenarios/partial", data={"scenario_id": sid})
            assert response.status_code == 200

    def test_partial_invalid_scenario_returns_fallback(self, client):
        response = client.post("/scenarios/partial", data={"scenario_id": "nonexistent_scenario"})
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestGenerateScenarioSolution:
    @pytest.mark.asyncio
    async def test_fallback_when_model_not_configured(self):
        with patch("app.scenarios.model", None):
            result = await generate_scenario_solution("lost_voter_id")
            assert isinstance(result, ScenarioResult)
            assert result.scenario_id == "lost_voter_id"
            assert len(result.steps) > 0

    @pytest.mark.asyncio
    async def test_unknown_scenario_returns_fallback(self):
        result = await generate_scenario_solution("nonexistent_scenario")
        assert isinstance(result, ScenarioResult)
        assert len(result.steps) > 0

    @pytest.mark.asyncio
    async def test_fallback_has_required_fields(self):
        with patch("app.scenarios.model", None):
            for sid in SCENARIOS:
                result = await generate_scenario_solution(sid)
                assert result.scenario_id == sid
                assert result.title
                assert result.description
                assert len(result.steps) > 0
                assert result.next_action
