from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.modeling.literature_modeling import run_modeling_pipeline


if __name__ == "__main__":
    result = run_modeling_pipeline(ROOT / "outputs" / "modeling")
    print("AKK modeling report generated")
    print(f"Report: {result['reportPath']}")
    print(f"Metrics: {result['metricsPath']}")
    print(f"Dataset: {result['datasetPath']}")
