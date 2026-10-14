import base64
from hashlib import sha256
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app

client = TestClient(app)


def _xlsx_base64() -> tuple[str, bytes]:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "培养记录"
    sheet.append(["time", "Temp", "pH"])
    sheet.append(["2026-01-01 00:00:00", 36.5, 6.8])
    sheet.append(["2026-01-01 00:05:00", 36.7, 6.75])
    buffer = BytesIO()
    workbook.save(buffer)
    raw = buffer.getvalue()
    return base64.b64encode(raw).decode("ascii"), raw


def test_upload_xlsx_parses_first_non_empty_sheet() -> None:
    content, raw = _xlsx_base64()
    response = client.post("/experiments/exp-xlsx/files", json={
        "fileName": "bioreactor.xlsx", "content": content, "encoding": "base64",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["detectedFormat"] == "xlsx"
    assert body["parseStatus"] == "parsed"
    assert body["columnNames"] == ["time", "Temp", "pH"]
    assert body["rowCount"] == 2
    assert body["contentHash"] == sha256(raw).hexdigest()


def test_upload_unknown_binary_is_preserved_for_adapter() -> None:
    raw = b"\x00DEVICE-RAW\xff\x10"
    response = client.post("/experiments/exp-raw/files", json={
        "fileName": "reactor.raw", "content": base64.b64encode(raw).decode("ascii"), "encoding": "base64",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["detectedFormat"] == "raw"
    assert body["parseStatus"] == "awaiting_adapter"
    assert body["columnNames"] == []
    assert body["rowCount"] == 0
    assert body["contentHash"] == sha256(raw).hexdigest()
    assert body["intakeRunId"] is None


def test_structured_file_can_record_raw_source_lineage() -> None:
    raw = client.post("/experiments/exp-derived/files", json={
        "fileName": "reactor.raw", "content": base64.b64encode(b"DEVICE-RAW").decode("ascii"), "encoding": "base64",
    }).json()
    converted = client.post("/experiments/exp-derived/files", json={
        "fileName": "reactor-converted.csv", "content": "time,Temp\n2026-01-01,36.5\n",
        "sourceAssetId": raw["assetId"],
        "sourceConversionNote": "设备导出文件经解密工具 v1.2 转换为 UTF-8 CSV。",
    })

    assert converted.status_code == 200
    body = converted.json()
    assert body["parseStatus"] == "parsed"
    assert body["derivedFromAssetId"] == raw["assetId"]
    assert body["sourceConversionNote"] == "设备导出文件经解密工具 v1.2 转换为 UTF-8 CSV。"
    assert body["intakeRunId"] is not None


def test_structured_file_rejects_source_asset_from_other_experiment() -> None:
    raw = client.post("/experiments/exp-source-a/files", json={
        "fileName": "reactor.raw", "content": base64.b64encode(b"DEVICE-RAW").decode("ascii"), "encoding": "base64",
    }).json()
    response = client.post("/experiments/exp-source-b/files", json={
        "fileName": "converted.csv", "content": "time,Temp\n2026-01-01,36.5\n", "sourceAssetId": raw["assetId"],
    })

    assert response.status_code == 422


def test_conversion_note_requires_a_source_asset() -> None:
    response = client.post("/experiments/exp-note-without-source/files", json={
        "fileName": "converted.csv", "content": "time,Temp\n2026-01-01,36.5\n",
        "sourceConversionNote": "adapter export v1.2",
    })

    assert response.status_code == 422
    assert "source conversion note" in response.json()["detail"]


def test_raw_source_cannot_be_deleted_while_a_structured_asset_depends_on_it() -> None:
    raw = client.post("/experiments/exp-lineage-delete/files", json={
        "fileName": "reactor.raw", "content": base64.b64encode(b"DEVICE-RAW").decode("ascii"), "encoding": "base64",
    }).json()
    derived = client.post("/experiments/exp-lineage-delete/files", json={
        "fileName": "reactor-converted.csv", "content": "time,Temp\n2026-01-01,36.5\n",
        "sourceAssetId": raw["assetId"],
    })
    assert derived.status_code == 200

    response = client.request(
        "DELETE", f"/experiments/exp-lineage-delete/files/{raw['assetId']}",
        json={"operator": "研发负责人", "reason": "检查原始文件删除保护"},
    )

    assert response.status_code == 409
    assert "derived" in response.json()["detail"]


def test_upload_experiment_text_file_creates_file_asset() -> None:
    response = client.post(
        "/experiments/exp-akk-001/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp,rpm\n2026-01-01 00:00:00,36.5,120\n",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-001"
    assert body["originalName"] == "bioreactor_temperature.csv"
    assert body["detectedFormat"] == "csv"
    assert body["parseStatus"] == "parsed"
    assert body["rowCount"] == 1
    assert body["columnNames"] == ["time", "Temp", "rpm"]
    assert body["contentHash"]
    assert body["duplicate"] is False


def test_upload_experiment_text_file_reuses_duplicate_content() -> None:
    first = client.post(
        "/experiments/exp-akk-dup/files",
        json={
            "fileName": "device_a.csv",
            "content": "time,value\n2026-01-01 00:00:00,1\n",
        },
    )
    second = client.post(
        "/experiments/exp-akk-dup/files",
        json={
            "fileName": "device_b.csv",
            "content": "time,value\n2026-01-01 00:00:00,1\n",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["duplicate"] is False
    assert second_body["duplicate"] is True
    assert second_body["assetId"] == first_body["assetId"]
    assert second_body["duplicateOfAssetId"] == first_body["assetId"]


def test_batch_upload_experiment_text_files_returns_assets() -> None:
    response = client.post(
        "/experiments/exp-akk-batch/files/batch",
        json={
            "files": [
                {
                    "fileName": "bioreactor_temperature.csv",
                    "content": "time,Temp\n2026-01-01 00:00:00,36.5\n",
                },
                {
                    "fileName": "ph_meter_log.csv",
                    "content": "time,pH\n2026-01-01 00:00:00,6.8\n",
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-batch"
    assert body["assetCount"] == 2
    assert [asset["originalName"] for asset in body["assets"]] == [
        "bioreactor_temperature.csv",
        "ph_meter_log.csv",
    ]
    assert [asset["columnNames"] for asset in body["assets"]] == [
        ["time", "Temp"],
        ["time", "pH"],
    ]
    assert [asset["duplicate"] for asset in body["assets"]] == [False, False]


def test_batch_upload_reuses_duplicate_content_within_same_experiment() -> None:
    response = client.post(
        "/experiments/exp-akk-batch-dup/files/batch",
        json={
            "files": [
                {
                    "fileName": "device_a.csv",
                    "content": "time,value\n2026-01-01 00:00:00,1\n",
                },
                {
                    "fileName": "device_b.csv",
                    "content": "time,value\n2026-01-01 00:00:00,1\n",
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assetCount"] == 2
    first, second = body["assets"]
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert second["assetId"] == first["assetId"]
    assert second["duplicateOfAssetId"] == first["assetId"]


def test_single_upload_writes_file_audit_event() -> None:
    upload = client.post(
        "/experiments/exp-akk-audit/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp\n2026-01-01 00:00:00,36.5\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    response = client.get("/experiments/exp-akk-audit/file-audits")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-audit"
    assert body["eventCount"] == 1
    event = body["events"][0]
    assert event["action"] == "upload_file"
    assert event["stage"] == "file_upload"
    assert event["stageLabel"] == "文件上传"
    assert event["fileNames"] == ["bioreactor_temperature.csv"]
    assert event["assetIds"] == [asset["assetId"]]
    assert event["contentHashes"] == [asset["contentHash"]]
    assert event["duplicates"] == [False]


def test_batch_upload_writes_file_audit_event() -> None:
    upload = client.post(
        "/experiments/exp-akk-batch-audit/files/batch",
        json={
            "files": [
                {
                    "fileName": "bioreactor_temperature.csv",
                    "content": "time,Temp\n2026-01-01 00:00:00,36.5\n",
                },
                {
                    "fileName": "ph_meter_log.csv",
                    "content": "time,pH\n2026-01-01 00:00:00,6.8\n",
                },
            ]
        },
    )

    assert upload.status_code == 200
    assets = upload.json()["assets"]
    response = client.get("/experiments/exp-akk-batch-audit/file-audits")

    assert response.status_code == 200
    body = response.json()
    assert body["eventCount"] == 1
    event = body["events"][0]
    assert event["action"] == "upload_files_batch"
    assert event["stage"] == "file_upload"
    assert event["stageLabel"] == "文件上传"
    assert event["fileNames"] == [
        "bioreactor_temperature.csv",
        "ph_meter_log.csv",
    ]
    assert event["assetIds"] == [asset["assetId"] for asset in assets]
    assert event["duplicates"] == [False, False]


def test_file_audit_summary_returns_stage_summary_and_last_event() -> None:
    first = client.post(
        "/experiments/exp-akk-summary/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp\n2026-01-01 00:00:00,36.5\n",
        },
    )
    second = client.post(
        "/experiments/exp-akk-summary/files/batch",
        json={
            "files": [
                {
                    "fileName": "ph_meter_log.csv",
                    "content": "time,pH\n2026-01-01 00:00:00,6.8\n",
                },
                {
                    "fileName": "od600_reader.csv",
                    "content": "time,OD600\n2026-01-01 00:00:00,0.42\n",
                },
            ]
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    response = client.get("/experiments/exp-akk-summary/file-audit-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-summary"
    assert body["eventCount"] == 2
    assert body["assetCount"] == 3
    assert body["stageSummary"] == [
        {
            "stage": "file_upload",
            "stageLabel": "文件上传",
            "eventCount": 2,
            "assetCount": 3,
        }
    ]
    assert body["lastEvent"]["action"] == "upload_files_batch"
    assert body["lastEvent"]["fileNames"] == ["ph_meter_log.csv", "od600_reader.csv"]


def test_list_experiment_file_assets_returns_uploaded_file_details() -> None:
    upload = client.post(
        "/experiments/exp-akk-assets/files/batch",
        json={
            "files": [
                {
                    "fileName": "bioreactor_temperature.csv",
                    "content": "time,Temp,rpm\n2026-01-01 00:00:00,36.5,120\n",
                },
                {
                    "fileName": "ph_meter_log.csv",
                    "content": "time,pH\n2026-01-01 00:00:00,6.8\n",
                },
            ]
        },
    )

    assert upload.status_code == 200
    response = client.get("/experiments/exp-akk-assets/files")

    assert response.status_code == 200
    body = response.json()
    assert [asset["originalName"] for asset in body] == [
        "bioreactor_temperature.csv",
        "ph_meter_log.csv",
    ]
    assert [asset["detectedFormat"] for asset in body] == ["csv", "csv"]
    assert [asset["rowCount"] for asset in body] == [1, 1]
    assert [asset["columnNames"] for asset in body] == [
        ["time", "Temp", "rpm"],
        ["time", "pH"],
    ]
    assert all(asset["contentHash"] for asset in body)


def test_field_mapping_suggestions_standardize_known_device_columns() -> None:
    upload = client.post(
        "/experiments/exp-akk-field-map/files/batch",
        json={
            "files": [
                {
                    "fileName": "bioreactor_temperature.csv",
                    "content": "time,Temp,rpm\n2026-01-01 00:00:00,36.5,120\n",
                },
                {
                    "fileName": "reader.csv",
                    "content": "timestamp,pH,OD600,UnknownSignal\n2026-01-01 00:00:00,6.8,0.42,7\n",
                },
            ]
        },
    )

    assert upload.status_code == 200
    response = client.get("/experiments/exp-akk-field-map/field-mapping-suggestions")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-field-map"
    assert body["assetCount"] == 2
    suggestions = {
        suggestion["originalColumn"]: suggestion
        for asset in body["assets"]
        for suggestion in asset["suggestions"]
    }
    assert suggestions["time"]["standardField"] == "timestamp"
    assert suggestions["time"]["confidenceScore"] == 0.95
    assert suggestions["time"]["requiresHumanConfirmation"] is False
    assert suggestions["Temp"]["standardField"] == "temperature_c"
    assert suggestions["Temp"]["unit"] == "°C"
    assert suggestions["rpm"]["standardField"] == "agitation_rpm"
    assert suggestions["pH"]["standardField"] == "ph"
    assert suggestions["OD600"]["standardField"] == "optical_density_600"
    assert suggestions["UnknownSignal"]["standardField"] is None
    assert suggestions["UnknownSignal"]["requiresHumanConfirmation"] is True


def test_confirm_field_mappings_saves_experiment_level_mapping_configuration() -> None:
    upload = client.post(
        "/experiments/exp-akk-confirm-map/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp,rpm\n2026-01-01 00:00:00,36.5,120\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    confirm = client.post(
        "/experiments/exp-akk-confirm-map/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "°C",
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    confirmed_body = confirm.json()
    assert confirmed_body["experimentId"] == "exp-akk-confirm-map"
    assert confirmed_body["mappingCount"] == 2
    assert confirmed_body["mappings"][0]["confirmed"] is True
    assert confirmed_body["mappings"][1]["standardField"] == "temperature_c"

    fetched = client.get("/experiments/exp-akk-confirm-map/field-mappings")

    assert fetched.status_code == 200
    fetched_body = fetched.json()
    assert fetched_body == confirmed_body


def test_custom_field_dictionary_teaches_suggestions_for_unknown_columns() -> None:
    upload = client.post(
        "/experiments/exp-akk-dictionary/files",
        json={
            "fileName": "custom_sensor.csv",
            "content": "time,UnknownSignal\n2026-01-01 00:00:00,7\n",
        },
    )

    assert upload.status_code == 200
    before = client.get("/experiments/exp-akk-dictionary/field-mapping-suggestions")
    before_suggestions = {
        suggestion["originalColumn"]: suggestion
        for asset in before.json()["assets"]
        for suggestion in asset["suggestions"]
    }
    assert before_suggestions["UnknownSignal"]["standardField"] is None

    dictionary = client.post(
        "/experiments/exp-akk-dictionary/field-dictionary",
        json={
            "entries": [
                {
                    "sourceColumn": "UnknownSignal",
                    "standardField": "custom_unknown_signal",
                    "displayName": "Custom unknown signal",
                    "unit": "a.u.",
                    "createdBy": "researcher",
                }
            ]
        },
    )

    assert dictionary.status_code == 200
    dictionary_body = dictionary.json()
    assert dictionary_body["experimentId"] == "exp-akk-dictionary"
    assert dictionary_body["entryCount"] == 1
    assert dictionary_body["entries"][0]["standardField"] == "custom_unknown_signal"

    after = client.get("/experiments/exp-akk-dictionary/field-mapping-suggestions")
    after_suggestions = {
        suggestion["originalColumn"]: suggestion
        for asset in after.json()["assets"]
        for suggestion in asset["suggestions"]
    }
    assert after_suggestions["UnknownSignal"]["standardField"] == "custom_unknown_signal"
    assert after_suggestions["UnknownSignal"]["unit"] == "a.u."
    assert after_suggestions["UnknownSignal"]["requiresHumanConfirmation"] is False
    assert after_suggestions["UnknownSignal"]["confidenceScore"] == 0.9


def test_cleaning_preview_uses_confirmed_mappings_and_reports_quality_issues() -> None:
    upload = client.post(
        "/experiments/exp-akk-cleaning/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp,rpm\n2026-01-01 00:00:00,36.5,120\n2026-01-01 00:05:00,,bad\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    confirm = client.post(
        "/experiments/exp-akk-cleaning/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "°C",
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "rpm",
                    "standardField": "agitation_rpm",
                    "displayName": "搅拌转速",
                    "unit": "rpm",
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    response = client.get("/experiments/exp-akk-cleaning/cleaning-preview")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-cleaning"
    assert body["assetCount"] == 1
    preview = body["assets"][0]
    assert preview["assetId"] == asset["assetId"]
    assert preview["rowCount"] == 2
    assert preview["cleanedRows"][0] == {
        "timestamp": "2026-01-01 00:00:00",
        "temperature_c": 36.5,
        "agitation_rpm": 120.0,
    }
    assert preview["quality"]["missingValueCount"] == 1
    assert preview["quality"]["invalidNumericCount"] == 1
    assert preview["quality"]["unmappedColumnCount"] == 0
    assert "Missing value: Temp at row 2" in preview["cleaningLogs"]
    assert "Invalid numeric value: rpm=bad at row 2" in preview["cleaningLogs"]


def test_alignment_preview_merges_cleaned_assets_by_timestamp() -> None:
    upload = client.post(
        "/experiments/exp-akk-align/files/batch",
        json={
            "files": [
                {
                    "fileName": "bioreactor_temperature.csv",
                    "content": "time,Temp\n2026-01-01 00:00:00,36.5\n2026-01-01 00:05:00,36.7\n",
                },
                {
                    "fileName": "ph_meter_log.csv",
                    "content": "time,pH\n2026-01-01 00:05:00,6.8\n2026-01-01 00:10:00,6.9\n",
                },
            ]
        },
    )

    assert upload.status_code == 200
    assets = upload.json()["assets"]
    confirm = client.post(
        "/experiments/exp-akk-align/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": assets[0]["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": assets[0]["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "°C",
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": assets[1]["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": assets[1]["assetId"],
                    "originalColumn": "pH",
                    "standardField": "ph",
                    "displayName": "pH",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    response = client.get("/experiments/exp-akk-align/alignment-preview")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-align"
    assert body["assetCount"] == 2
    assert body["timestampCount"] == 3
    assert body["missingCellCount"] == 2
    assert body["alignedRows"] == [
        {
            "timestamp": "2026-01-01 00:00:00",
            "temperature_c": 36.5,
            "ph": None,
        },
        {
            "timestamp": "2026-01-01 00:05:00",
            "temperature_c": 36.7,
            "ph": 6.8,
        },
        {
            "timestamp": "2026-01-01 00:10:00",
            "temperature_c": None,
            "ph": 6.9,
        },
    ]
    assert body["assetSummaries"][0]["timestampCount"] == 2
    assert body["assetSummaries"][1]["timestampCount"] == 2
    assert "Missing aligned value: ph at 2026-01-01 00:00:00" in body["alignmentLogs"]


def test_feature_preview_computes_statistics_delta_and_anomaly_hints() -> None:
    upload = client.post(
        "/experiments/exp-akk-feature/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp\n2026-01-01 00:00:00,36.5\n2026-01-01 00:05:00,36.7\n2026-01-01 00:10:00,45.0\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    confirm = client.post(
        "/experiments/exp-akk-feature/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "°C",
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    response = client.get("/experiments/exp-akk-feature/feature-preview")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-feature"
    assert body["rowCount"] == 3
    feature = body["features"][0]
    assert feature["field"] == "temperature_c"
    assert feature["count"] == 3
    assert feature["min"] == 36.5
    assert feature["max"] == 45.0
    assert feature["mean"] == 39.4
    assert feature["first"] == 36.5
    assert feature["last"] == 45.0
    assert feature["delta"] == 8.5
    assert feature["windowMean"] == 39.4
    assert body["anomalyHints"][0]["field"] == "temperature_c"
    assert body["anomalyHints"][0]["timestamp"] == "2026-01-01 00:10:00"
    assert body["anomalyHints"][0]["value"] == 45.0


def test_dataset_snapshot_packages_modeling_ready_experiment_state() -> None:
    upload = client.post(
        "/experiments/exp-akk-snapshot/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp\n2026-01-01 00:00:00,36.5\n2026-01-01 00:05:00,36.7\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    confirm = client.post(
        "/experiments/exp-akk-snapshot/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "°C",
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    created = client.post("/experiments/exp-akk-snapshot/dataset-snapshots")

    assert created.status_code == 200
    body = created.json()
    assert body["experimentId"] == "exp-akk-snapshot"
    assert body["snapshotId"].startswith("dataset-")
    assert body["assetCount"] == 1
    assert body["mappingCount"] == 2
    assert body["alignedRowCount"] == 2
    assert body["featureCount"] == 1
    assert body["anomalyCount"] == 0
    assert body["contentHash"]
    assert body["status"] == "modeling_ready"
    assert body["createdAt"]

    latest = client.get("/experiments/exp-akk-snapshot/dataset-snapshots/latest")

    assert latest.status_code == 200
    assert latest.json() == body


def test_modeling_plan_preview_builds_demo_ready_training_plan() -> None:
    upload = client.post(
        "/experiments/exp-akk-modeling/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp,pH\n2026-01-01 00:00:00,36.5,6.8\n2026-01-01 00:05:00,36.7,6.9\n2026-01-01 00:10:00,37.2,7.0\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    confirm = client.post(
        "/experiments/exp-akk-modeling/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "℃",
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "pH",
                    "standardField": "ph",
                    "displayName": "酸碱度",
                    "unit": "pH",
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    created = client.post("/experiments/exp-akk-modeling/dataset-snapshots")

    assert created.status_code == 200
    response = client.get("/experiments/exp-akk-modeling/modeling-plan-preview")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-modeling"
    assert body["snapshotId"] == created.json()["snapshotId"]
    assert body["targetField"] == "temperature_c"
    assert body["recommendedModelType"] == "time_series_regression"
    assert body["trainSplitRatio"] == 0.8
    assert body["validationSplitRatio"] == 0.2
    assert body["candidateFeatures"] == ["ph"]
    assert "mae" in body["evaluationMetrics"]
    assert "r2" in body["evaluationMetrics"]
    assert body["status"] == "draft_ready"
    assert body["riskHints"]
    assert any("aligned rows" in hint.lower() for hint in body["riskHints"])


def test_training_task_preview_creates_multi_agent_demo_execution() -> None:
    upload = client.post(
        "/experiments/exp-akk-training/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp,pH\n2026-01-01 00:00:00,36.5,6.8\n2026-01-01 00:05:00,36.7,6.9\n2026-01-01 00:10:00,37.2,7.0\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    confirm = client.post(
        "/experiments/exp-akk-training/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "℃",
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "pH",
                    "standardField": "ph",
                    "displayName": "酸碱度",
                    "unit": "pH",
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    snapshot = client.post("/experiments/exp-akk-training/dataset-snapshots")

    assert snapshot.status_code == 200
    created = client.post("/experiments/exp-akk-training/training-tasks")

    assert created.status_code == 200
    body = created.json()
    assert body["experimentId"] == "exp-akk-training"
    assert body["snapshotId"] == snapshot.json()["snapshotId"]
    assert body["planTargetField"] == "temperature_c"
    assert body["status"] == "queued"
    assert body["recommendedModelType"] == "time_series_regression"
    assert body["agentStages"][0]["agentName"] == "data_agent"
    assert body["agentStages"][1]["agentName"] == "modeling_agent"
    assert body["agentStages"][2]["agentName"] == "report_agent"
    assert body["evaluationMetrics"] == ["mae", "rmse", "r2"]
    assert body["taskId"].startswith("train-")

    latest = client.get("/experiments/exp-akk-training/training-tasks/latest")

    assert latest.status_code == 200
    latest_body = latest.json()
    assert latest_body["taskId"] == body["taskId"]
    assert latest_body["status"] in ["running", "completed"]


def test_training_result_summary_returns_metrics_confidence_and_recommendations() -> None:
    upload = client.post(
        "/experiments/exp-akk-result/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp,pH\n2026-01-01 00:00:00,36.5,6.8\n2026-01-01 00:05:00,36.7,6.9\n2026-01-01 00:10:00,37.2,7.0\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    confirm = client.post(
        "/experiments/exp-akk-result/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "℃",
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "pH",
                    "standardField": "ph",
                    "displayName": "酸碱度",
                    "unit": "pH",
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    snapshot = client.post("/experiments/exp-akk-result/dataset-snapshots")
    assert snapshot.status_code == 200
    created = client.post("/experiments/exp-akk-result/training-tasks")
    assert created.status_code == 200
    latest = client.get("/experiments/exp-akk-result/training-tasks/latest")
    assert latest.status_code == 200

    response = client.get("/experiments/exp-akk-result/training-results/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-result"
    assert body["taskId"] == created.json()["taskId"]
    assert body["targetField"] == "temperature_c"
    assert body["status"] in ["ready", "completed"]
    assert body["confidenceLevel"] in ["medium", "high"]
    assert body["metrics"]["mae"] >= 0
    assert body["metrics"]["rmse"] >= 0
    assert 0 <= body["metrics"]["r2"] <= 1
    assert body["riskNotes"]
    assert body["recommendations"]
    assert body["manualReviewItems"]


def test_research_brief_summary_packages_training_findings_for_handoff() -> None:
    upload = client.post(
        "/experiments/exp-akk-brief/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp,pH\n2026-01-01 00:00:00,36.5,6.8\n2026-01-01 00:05:00,36.7,6.9\n2026-01-01 00:10:00,37.2,7.0\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    confirm = client.post(
        "/experiments/exp-akk-brief/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "℃",
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "pH",
                    "standardField": "ph",
                    "displayName": "酸碱度",
                    "unit": "pH",
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    assert client.post("/experiments/exp-akk-brief/dataset-snapshots").status_code == 200
    created = client.post("/experiments/exp-akk-brief/training-tasks")
    assert created.status_code == 200
    assert client.get("/experiments/exp-akk-brief/training-results/latest").status_code == 200

    response = client.get("/experiments/exp-akk-brief/research-brief/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-brief"
    assert body["taskId"] == created.json()["taskId"]
    assert body["title"]
    assert body["objective"]
    assert body["dataSummary"]
    assert body["modelSummary"]
    assert body["riskSummary"]
    assert body["nextActions"]
    assert body["manualConfirmationItems"]
    assert body["status"] in ["draft_ready", "completed"]


def test_simulation_input_summary_generates_candidate_process_plans() -> None:
    upload = client.post(
        "/experiments/exp-akk-sim/files",
        json={
            "fileName": "bioreactor_temperature.csv",
            "content": "time,Temp,pH\n2026-01-01 00:00:00,36.5,6.8\n2026-01-01 00:05:00,36.7,6.9\n2026-01-01 00:10:00,37.2,7.0\n",
        },
    )

    assert upload.status_code == 200
    asset = upload.json()
    confirm = client.post(
        "/experiments/exp-akk-sim/field-mappings/confirm",
        json={
            "mappings": [
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "time",
                    "standardField": "timestamp",
                    "displayName": "时间戳",
                    "unit": None,
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "Temp",
                    "standardField": "temperature_c",
                    "displayName": "温度",
                    "unit": "℃",
                    "confirmedBy": "researcher",
                },
                {
                    "assetId": asset["assetId"],
                    "originalColumn": "pH",
                    "standardField": "ph",
                    "displayName": "酸碱度",
                    "unit": "pH",
                    "confirmedBy": "researcher",
                },
            ]
        },
    )

    assert confirm.status_code == 200
    assert client.post("/experiments/exp-akk-sim/dataset-snapshots").status_code == 200
    assert client.post("/experiments/exp-akk-sim/training-tasks").status_code == 200
    assert client.get("/experiments/exp-akk-sim/training-results/latest").status_code == 200
    assert client.get("/experiments/exp-akk-sim/research-brief/latest").status_code == 200

    response = client.get("/experiments/exp-akk-sim/simulation-inputs/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["experimentId"] == "exp-akk-sim"
    assert body["targetField"] == "temperature_c"
    assert body["objective"]
    assert body["recommendedRanges"]["temperature_c"]["min"] <= body["recommendedRanges"]["temperature_c"]["max"]
    assert body["recommendedRanges"]["ph"]["min"] <= body["recommendedRanges"]["ph"]["max"]
    assert len(body["candidatePlans"]) == 3
    assert body["candidatePlans"][0]["planName"]
    assert body["candidatePlans"][0]["reason"]
    assert body["manualConfirmationItems"]
    assert body["status"] in ["draft_ready", "completed"]
