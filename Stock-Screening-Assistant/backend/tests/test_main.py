# tests/test_main.py
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)

def test_parse_endpoint():
    # Valid case
    response = client.post("/parse", json={"query": "tech stocks under $50"})
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert "intent" in response.json()

    # Error case (empty query)
    response = client.post("/parse", json={"query": ""})
    assert response.status_code == 400
    

def test_screen_endpoint():
    request_data = {
        "intent": "screen",
        "sector": "Technology",
        "filters": {
            "price_under": 400,
            "peRatio_lt": 40,
            "debtToEquity_lt": 2,
        },
        "metrics": ["price", "peRatio", "marketCap"],
        "limit": 2
    }
    # Valid case
    response = client.post("/screen", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["results"]) == 2
    assert data["after_filters"] == 2
    print(f"Stocks: {data['results']}")

    # Check that metrics are included
    for stock in data["results"]:
        assert "symbol" in stock
        assert "price" in stock
        assert "peRatio" in stock
        assert "marketCap" in stock

def test_screen_unsupported_intent():
    """Test that only 'screen' intent is allowed"""
    request_data = {
        "intent": "invalid_intent",
        "sector": "Technology"
    }

    response = client.post("/screen", json=request_data)
    assert response.status_code == 400
    assert "Unsupported intent" in response.json()["error"]

