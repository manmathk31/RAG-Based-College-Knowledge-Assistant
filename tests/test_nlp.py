import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_sentiment_endpoint():
    payload = {"text": "The faculty is supportive and the library is great, but the mess food is terrible."}
    response = client.post("/api/v1/nlp/sentiment", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Basic sanity checks
    assert data["overall_sentiment"] in ["positive", "negative", "neutral"]
    assert isinstance(data["confidence"], float)
    assert isinstance(data["polarity_score"], float)
    assert isinstance(data["aspects"], list)
    assert isinstance(data["summary"], str)


def test_entity_extraction_endpoint():
    payload = {"text": "First Year B.Tech Computer Engineering fee is Rs. 1,65,000. Admission requires 45% marks in 10+2 and a JEE Main score. Placement drives start in Semester 7 with IBM and Cisco offering up to 24 LPA."}
    response = client.post("/api/v1/nlp/extract-entities", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["total_entities"], int)
    assert isinstance(data["entity_counts"], dict)
    assert isinstance(data["entities"], list)
    # Confirm at least one course and one fee entity were extracted
    categories = [e["category"] for e in data["entities"]]
    assert "COURSE" in categories
    assert "FEE" in categories
    assert "PLACEMENT" in categories

if __name__ == "__main__":
    # Run tests manually for quick verification
    test_sentiment_endpoint()
    test_entity_extraction_endpoint()
    print("All NLP endpoint tests passed.")
