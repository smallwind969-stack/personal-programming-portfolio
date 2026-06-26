from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_system_status() -> None:
    response = client.get("/system/status")
    assert response.status_code == 200
    status = response.json()
    assert status["status"] == "ok"
    assert status["productCount"] >= 1
    assert status["knowledgeItemCount"] >= 1
    assert status["knowledgeChunkCount"] >= 1
    assert status["researchUseOnly"] is True


def test_list_products() -> None:
    response = client.get("/akk-products")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 1
    assert products[0]["sourceType"] == "mock"


def test_product_detail() -> None:
    response = client.get("/akk-products/akk-postbiotic-powder")
    assert response.status_code == 200
    assert response.json()["productId"] == "akk-postbiotic-powder"


def test_generate_formula() -> None:
    response = client.post(
        "/formula/generate",
        json={
            "applicationTargetId": "nutrition_powder",
            "targetProperties": ["gut health concept fit"],
            "constraints": ["sensory check required"],
            "preferredProductIds": ["akk-postbiotic-powder", "akk-fiber-complex"],
            "excludedProductIds": [],
            "maxIngredientCount": 2,
            "notes": "mock test",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["research_use_only"] is True
    assert result["researchUseOnly"] is True
    assert result["candidates"][0]["composition"]
    assert result["candidates"][0]["predictions"]
    assert result["candidates"][0]["riskItems"]
    assert result["candidates"][0]["experimentSuggestions"]
    assert result["candidates"][0]["companionIngredients"]
    assert result["candidates"][0]["knowledgeReferences"]
    assert result["candidates"][0]["agentTrace"]


def test_get_formula_result() -> None:
    response = client.get("/formula-results/mock-result-001")
    assert response.status_code == 200
    assert response.json()["research_use_only"] is True


def test_list_formula_results() -> None:
    response = client.get("/formula-results")
    assert response.status_code == 200
    assert response.json()[0]["research_use_only"] is True


def test_list_knowledge_items() -> None:
    response = client.get("/knowledge", params={"query": "low sugar yogurt"})
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert items[0]["knowledgeId"]
    assert items[0]["usableInsights"]
    assert "retrievalScore" in items[0]
    assert "matchReasons" in items[0]
    assert "validationMetrics" in items[0]


def test_list_knowledge_chunks() -> None:
    response = client.get("/knowledge/chunks", params={"query": "low sugar yogurt", "limit": 5})
    assert response.status_code == 200
    chunks = response.json()
    assert len(chunks) >= 1
    assert chunks[0]["chunkId"]
    assert chunks[0]["text"]
    assert chunks[0]["retrievalScore"] > 0


def test_generate_formula_uses_literature_references() -> None:
    response = client.post(
        "/formula/generate",
        json={
            "applicationTargetId": "yogurt",
            "targetProperties": ["low sugar", "gut health concept"],
            "constraints": ["clean label", "medium cost"],
            "preferredProductIds": ["akk-postbiotic-powder", "akk-metabolite-blend"],
            "excludedProductIds": [],
            "maxIngredientCount": 2,
            "notes": "female low sugar yogurt, clean taste, medium cost",
        },
    )
    assert response.status_code == 200
    references = response.json()["candidates"][0]["knowledgeReferences"]
    assert references
    assert references[0]["evidenceLevel"] in {"A", "B", "C", "D"}
    assert references[0]["relevanceReason"]
    assert "retrievalScore" in references[0]
    assert "keyPassages" in references[0]


def test_llm_status() -> None:
    response = client.get("/llm/status")
    assert response.status_code == 200
    status = response.json()
    assert "enabled" in status
    assert status["provider"]
    assert status["model"]


def test_list_experiments() -> None:
    response = client.get("/experiments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
