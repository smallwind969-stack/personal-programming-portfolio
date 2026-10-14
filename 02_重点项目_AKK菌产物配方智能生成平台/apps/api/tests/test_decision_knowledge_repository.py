import json

from app.decision.knowledge_repository import JsonKnowledgeRepository


def _write_knowledge(path):
    path.write_text(
        json.dumps(
            {
                "version": "knowledge-test-v1",
                "entries": [
                    {
                        "evidenceId": "jelly-active",
                        "productTypes": ["功能性果冻"],
                        "metrics": ["springiness"],
                        "source": {
                            "title": "Jelly texture study",
                            "url": "https://example.org/jelly",
                            "location": "Table 2",
                        },
                        "evidenceKind": "author_table",
                        "evidenceLevel": "peer_reviewed_direct",
                        "contentFingerprint": "sha256:aabbccddeeff0011",
                        "version": "1",
                        "status": "active",
                    },
                    {
                        "evidenceId": "jelly-disabled",
                        "productTypes": ["功能性果冻"],
                        "metrics": ["springiness"],
                        "source": {"title": "Retired evidence", "file": "retired.csv"},
                        "evidenceKind": "internal_record",
                        "evidenceLevel": "internal_unverified",
                        "contentFingerprint": "sha256:1122334455667788",
                        "version": "1",
                        "status": "disabled",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_repository_returns_only_active_evidence_with_sources_and_lineage(tmp_path):
    knowledge_path = tmp_path / "knowledge.json"
    _write_knowledge(knowledge_path)
    repository = JsonKnowledgeRepository(knowledge_path)

    matches = repository.search(product_type="功能性果冻", metrics=["springiness"])

    assert [item.evidenceId for item in matches] == ["jelly-active"]
    assert matches[0].evidenceLevel == "peer_reviewed_direct"
    assert matches[0].contentFingerprint == "sha256:aabbccddeeff0011"


def test_repository_reports_insufficient_knowledge_instead_of_default_formula(tmp_path):
    knowledge_path = tmp_path / "knowledge.json"
    knowledge_path.write_text('{"version":"empty-v1","entries":[]}', encoding="utf-8")

    assert JsonKnowledgeRepository(knowledge_path).search(
        product_type="功能性果冻", metrics=["springiness"]
    ) == []


def test_repository_matches_domain_qualified_product_type(tmp_path):
    knowledge_path = tmp_path / "knowledge.json"
    knowledge_path.write_text(
        json.dumps(
            {
                "version": "knowledge-test-v1",
                "entries": [
                    {
                        "evidenceId": "functional-jelly",
                        "productTypes": ["功能性果冻"],
                        "metrics": ["target_product_output"],
                        "source": {
                            "title": "Jelly evidence",
                            "url": "https://example.org/jelly",
                        },
                        "evidenceKind": "author_table",
                        "evidenceLevel": "peer_reviewed_direct",
                        "contentFingerprint": "sha256:aabbccddeeff0011",
                        "version": "1",
                        "status": "active",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    matches = JsonKnowledgeRepository(knowledge_path).search(
        product_type="菌藻功能性果冻",
        metrics=["target_product_output"],
    )

    assert [item.evidenceId for item in matches] == ["functional-jelly"]
