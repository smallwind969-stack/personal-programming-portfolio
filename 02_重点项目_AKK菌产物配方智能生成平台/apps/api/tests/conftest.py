"""Keep API tests away from the user's persistent demonstration workspace."""

import os
import tempfile


# This module is imported by pytest before test modules import the application.
# A per-run database prevents TestClient workflows from adding fake experiments
# to data/akk_platform.sqlite3 (the database used by the local demo server).
_test_runtime = tempfile.mkdtemp(prefix="akk-api-tests-")
os.environ.setdefault(
    "EXPERIMENT_WORKSPACE_DB_PATH",
    os.path.join(_test_runtime, "experiment-workspaces.db"),
)
os.environ.setdefault("AUTH_DB_PATH", os.path.join(_test_runtime, "auth.db"))
os.environ.setdefault(
    "MODEL_REGISTRY_PATH", os.path.join(_test_runtime, "model-registry.db")
)
os.environ.setdefault(
    "RESEARCH_ARTIFACT_PATH", os.path.join(_test_runtime, "model-artifacts")
)
os.environ.setdefault(
    "DECISION_TRACE_DB_PATH", os.path.join(_test_runtime, "decision-traces.db")
)
os.environ.setdefault("BOOTSTRAP_ADMIN_USERNAME", "admin")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "Test-Admin-2026!")
