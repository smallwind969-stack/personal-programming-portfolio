from __future__ import annotations

from datetime import datetime, timezone
from random import Random

from app.repositories.mock_repository import MockRepository
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.experiments import ExperimentRecord


class ExperimentService:
    def __init__(self, repository: SqliteRepository | None = None) -> None:
        self.repository = repository or SqliteRepository()
        self.mock_repository = MockRepository()

    def create_synthetic_records_for_result(self, result: dict) -> list[ExperimentRecord]:
        result_id = result["resultId"]
        candidate = result["candidates"][0]
        seed = sum(ord(char) for char in result_id)
        random = Random(seed)
        high_risk_count = len([risk for risk in candidate["riskItems"] if risk["riskLevel"] == "high"])
        risk_pressure = max(0, min(12, high_risk_count * 2.2))

        templates = [
            ("活性标志物保留率", "%", ">= 70%", 74 + random.random() * 16 - risk_pressure, "越高越好"),
            ("酸性体系稳定性", "score", ">= 75", 72 + random.random() * 18 - risk_pressure, "越高越好"),
            ("浊度变化", "%", "<= 10%", 5 + random.random() * 8 + risk_pressure / 2, "越低越好"),
            ("感官接受度", "score", ">= 80", 76 + random.random() * 16 - risk_pressure / 2, "越高越好"),
            ("复水/分散表现", "score", ">= 75", 74 + random.random() * 18 - risk_pressure / 3, "越高越好"),
            ("单位样品成本指数", "index", "<= 75", 58 + random.random() * 22 + risk_pressure / 2, "越低越好"),
        ]

        records = []
        now = datetime.now(timezone.utc).isoformat()
        for index, (test_name, unit, target_range, value, direction) in enumerate(templates, start=1):
            value = round(value, 1)
            status = self._status(test_name, value)
            risk_level = "low" if status == "pass" else "medium" if status == "watch" else "high"
            records.append(
                {
                    "experimentId": f"exp-{result_id}-{index}",
                    "resultId": result_id,
                    "sampleCode": f"{candidate['candidateName']}-S{index:02d}",
                    "testName": test_name,
                    "metricValue": value,
                    "unit": unit,
                    "targetRange": target_range,
                    "status": status,
                    "riskLevel": risk_level,
                    "conclusion": self._conclusion(test_name, status, direction),
                    "createdAt": now,
                }
            )

        self.repository.save_experiment_records(result_id, records)
        return [ExperimentRecord.model_validate(record) for record in records]

    def list_records(self, result_id: str | None = None) -> list[ExperimentRecord]:
        if result_id is None and not self.repository.list_experiment_records(None):
            for result in self.mock_repository.get_formula_results()[:1]:
                self.create_synthetic_records_for_result(result)
        return [
            ExperimentRecord.model_validate(self._to_schema_keys(record))
            for record in self.repository.list_experiment_records(result_id)
        ]

    def _to_schema_keys(self, record: dict) -> dict:
        return {
            "experimentId": record["experiment_id"],
            "resultId": record["result_id"],
            "sampleCode": record["sample_code"],
            "testName": record["test_name"],
            "metricValue": record["metric_value"],
            "unit": record["unit"],
            "targetRange": record["target_range"],
            "status": record["status"],
            "riskLevel": record["risk_level"],
            "conclusion": record["conclusion"],
            "createdAt": record["created_at"],
        }

    def _status(self, test_name: str, value: float) -> str:
        if test_name in {"浊度变化", "单位样品成本指数"}:
            threshold = 10 if test_name == "浊度变化" else 75
            watch_threshold = 15 if test_name == "浊度变化" else 85
            if value <= threshold:
                return "pass"
            return "watch" if value <= watch_threshold else "fail"
        if value >= 80:
            return "pass"
        if value >= 70:
            return "watch"
        return "fail"

    def _conclusion(self, test_name: str, status: str, direction: str) -> str:
        if status == "pass":
            return f"{test_name}达到当前工业打样目标，可进入下一轮客户样品评审。"
        if status == "watch":
            return f"{test_name}接近目标，下一轮小试需要做梯度优化；指标方向为{direction}。"
        return f"{test_name}未达到目标，建议调整配方比例或工艺条件后重新打样。"


experiment_service = ExperimentService()
