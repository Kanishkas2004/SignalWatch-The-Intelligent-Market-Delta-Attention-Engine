import pytest
from starlette.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "data_feed" in data


def test_get_users_and_watchlists(client):
    # Test users list
    user_res = client.get("/api/users")
    assert user_res.status_code == 200
    users = user_res.json()
    assert len(users) >= 1
    user_id = users[0]["id"]

    # Test user's watchlists
    wl_res = client.get(f"/api/users/{user_id}/watchlists")
    assert wl_res.status_code == 200
    watchlists = wl_res.json()
    assert len(watchlists) >= 1
    assert len(watchlists[0]["items"]) >= 1


def test_watchlist_analysis_with_attention_scores(client):
    user_res = client.get("/api/users")
    user_id = user_res.json()[0]["id"]
    wl_res = client.get(f"/api/users/{user_id}/watchlists")
    wl_id = wl_res.json()[0]["id"]

    analysis_res = client.get(f"/api/watchlists/{wl_id}/analysis")
    assert analysis_res.status_code == 200
    data = analysis_res.json()

    assert "executive_digest" in data
    assert "tickers" in data
    assert "comparison_snapshot" in data
    assert len(data["tickers"]) > 0

    first_ticker = data["tickers"][0]
    assert "attention" in first_ticker
    assert "composite_score" in first_ticker["attention"]
    assert "tier" in first_ticker["attention"]
    assert first_ticker["attention"]["tier"] in ["PRIORITY", "NOTEWORTHY", "STEADY"]
    assert len(first_ticker["attention"]["reasons"]) > 0


def test_time_machine_simulation(client):
    user_res = client.get("/api/users")
    user_id = user_res.json()[0]["id"]

    sim_res = client.post(
        f"/api/users/{user_id}/snapshots/simulate",
        json={"simulated_minutes_ago": 180}  # 3 hours ago
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "id" in sim_data
    assert "Simulated" in sim_data["label"]


def test_ticker_search_and_add_item(client):
    search_res = client.get("/api/tickers/search?q=NVDA")
    assert search_res.status_code == 200
    results = search_res.json()
    assert any(r["symbol"] == "NVDA" for r in results)

    # Get watchlist and add item
    user_res = client.get("/api/users")
    user_id = user_res.json()[0]["id"]
    wl_res = client.get(f"/api/users/{user_id}/watchlists")
    wl_id = wl_res.json()[0]["id"]

    # Try adding a new ticker
    add_res = client.post(
        f"/api/watchlists/{wl_id}/items",
        json={
            "symbol": "SNOW",
            "custom_notes": "Cloud data momentum test",
            "tags": ["SaaS", "Cloud"],
            "custom_sensitivity": "high"
        }
    )
    assert add_res.status_code in [200, 400]  # 400 if already present, 200 if new
