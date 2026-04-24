import json
import os
import logging
import psycopg
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from src.api.schemas import AnalyzeRequest, AnalyzeResponse, ViolationItem
from src.anonymization.csv_loader import load_tenant_csvs
from src.anonymization.field_mapper import anonymize_dataframe
from src.anonymization.db_writer import write_tenant_data
from src.agent_layer.orchestrator import run_compliance_analysis
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'tenant_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'rasika23')

router = APIRouter()

def get_db_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=False
    )


def ensure_evaluation_results_table(conn: psycopg.Connection) -> None:
    """
    Create evaluation_results if missing, so inserts never fail silently.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.evaluation_results (
                id BIGSERIAL PRIMARY KEY,
                tenant_id character varying(32) NOT NULL,
                result_json jsonb NOT NULL,
                risk_score numeric(5,2) NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evaluation_results_tenant_id
            ON public.evaluation_results (tenant_id)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evaluation_results_created_at
            ON public.evaluation_results (created_at DESC)
            """
        )


def build_violation_items(analysis_result: dict) -> list[ViolationItem]:
    grouped: dict[str, dict] = {}
    contributions = analysis_result.get("risk_contributions", {})

    for violation in analysis_result.get("violations", []):
        rule_id = violation.get("rule_id")
        if not rule_id:
            continue

        if rule_id not in grouped:
            grouped[rule_id] = {
                "rule_id": rule_id,
                "rule_name": violation.get("rule_name", rule_id),
                "dpdp_section": violation.get("dpdp_section", ""),
                "severity": violation.get("severity", "MEDIUM"),
                "risk_weight": float(violation.get("risk_weight", 0.0)),
                "occurrence_count": 0,
                "reasons": [],
                "matched_record_ids": set(),
            }

        entry = grouped[rule_id]
        entry["occurrence_count"] += 1

        record_id = violation.get("record_id")
        if record_id:
            entry["matched_record_ids"].add(str(record_id))

        for reason in violation.get("signal_reasons", []):
            if reason and reason not in entry["reasons"]:
                entry["reasons"].append(reason)

    items: list[ViolationItem] = []
    for rule_id, entry in grouped.items():
        matched_record_ids = sorted(entry["matched_record_ids"])
        reason_text = "; ".join(entry["reasons"]) if entry["reasons"] else f"{entry['rule_name']} triggered"

        items.append(
            ViolationItem(
                rule_id=entry["rule_id"],
                rule_name=entry["rule_name"],
                dpdp_section=entry["dpdp_section"],
                severity=entry["severity"],
                risk_weight=entry["risk_weight"],
                occurrence_count=entry["occurrence_count"],
                contribution_to_score=float(contributions.get(rule_id, 0.0)),
                reason=reason_text,
                explanation=None,
                matched_record_ids=matched_record_ids,
                fields_triggered=[],
                matched_logs_count=len(matched_record_ids),
            )
        )

    return sorted(items, key=lambda x: x.rule_id)


@router.get("/health")
def health_check():
    """
    Simple health check endpoint.
    Visit http://localhost:8000/health to confirm API is running.
    """
    return {
        "status": "running",
        "service": "DPDP Compliance Engine"
    }

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_tenant(request: AnalyzeRequest):
    """
    Run full compliance check for a known tenant.

    Input:
        { "tenant_id": "tenant_b" }

    Output:
        Full compliance report with violations and risk score
    """
    try:
        result = run_compliance_analysis(request.tenant_id)
        violations = build_violation_items(result)

        return AnalyzeResponse(
            tenant_id=request.tenant_id,
            unique_rules_violated=len(violations),
            total_violation_occurrences=sum(v.occurrence_count for v in violations),
            risk_score=float(result.get("risk_score", 0.0)),
            risk_tier=result.get("risk_tier", "COMPLIANT"),
            violations=violations,
            status="success"
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code = 404,
            detail      = f"Tenant '{request.tenant_id}' not found. "
                          f"Check that redacted files exist."
        )
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail      = f"Analysis failed: {str(e)}"
        )


@router.post("/analyze/upload", response_model=AnalyzeResponse)
async def analyze_upload(
    governance_config: UploadFile = File(...),
    customer_master: UploadFile = File(...),
    consent_records: UploadFile = File(...),
    transaction_events: UploadFile = File(...),
    access_logs: UploadFile = File(...),
    data_lifecycle: UploadFile = File(...),
    security_events: UploadFile = File(...),
    dsar_requests: UploadFile = File(...),
    system_inventory: UploadFile = File(...),
    policies: UploadFile = File(...),
    tenant_id: str = Form(...),
    tenant_name: str = Form(...)
):
    """
    Run full compliance check on 10 uploaded CSV files.

    Input:
        10 CSV files uploaded:
        - governance_config.csv
        - customer_master.csv
        - consent_records.csv
        - transaction_events.csv
        - access_logs.csv
        - data_lifecyle.csv
        - security_events.csv
        - dsar_requests.csv
        - system_inventory.csv
        - policies.csv
        - tenant_id (form field)
        - tenant_name (form field)

    Flow:
        1. Receive 10 CSV files
        2. Pass directly to csv_loader.py for anonymization
        4. Run compliance check
        5. Return report

    Output:
        Full compliance report with violations and risk score
    """
    try:
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()

            uploaded_file_map = {
                "governance_config.csv": governance_config,
                "customer_master.csv": customer_master,
                "consent_records.csv": consent_records,
                "transaction_events.csv": transaction_events,
                "access_logs.csv": access_logs,
                "data_lifecycle.csv": data_lifecycle,
                "security_events.csv": security_events,
                "dsar_requests.csv": dsar_requests,
                "system_inventory.csv": system_inventory,
                "policies.csv": policies,
            }

            for csv_filename, uploaded_file in uploaded_file_map.items():
                csv_bytes = await uploaded_file.read()
                csv_path = Path(temp_dir) / csv_filename
                with open(csv_path, "wb") as f:
                    f.write(csv_bytes)

            loaded_data = load_tenant_csvs(Path(temp_dir), tenant_id)
            mapped_data = {}
            for table_name, df in loaded_data.items():
                mapped_data[table_name] = anonymize_dataframe(df, table_name, tenant_id)

            rows_written = write_tenant_data(tenant_id, mapped_data)
            
        except Exception as loader_error:
            raise HTTPException(
                status_code=500,
                detail=f"CSV ingestion failed: {str(loader_error)}"
            )
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        db_tenant_id = tenant_id
        analysis_result = run_compliance_analysis(db_tenant_id)
        violations = build_violation_items(analysis_result)

        response_payload = {
            "tenant_id": str(db_tenant_id),
            "tenant_name": tenant_name,
            "unique_rules_violated": len(violations),
            "total_violation_occurrences": sum(v.occurrence_count for v in violations),
            "risk_score": float(analysis_result.get("risk_score", 0.0)),
            "risk_tier": analysis_result.get("risk_tier", "COMPLIANT"),
            "rows_written": rows_written,
            "violations": [v.dict() for v in violations],
            "status": "success",
        }

        try:
            with get_db_connection() as conn:
                ensure_evaluation_results_table(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO evaluation_results (tenant_id, result_json, risk_score) VALUES (%s, %s, %s)",
                        (
                            db_tenant_id,
                            json.dumps(response_payload),
                            float(response_payload["risk_score"]),
                        ),
                    )
                conn.commit()
        except Exception as db_ex:
            logging.warning(f"evaluation_results insert failed: {db_ex}")

        return AnalyzeResponse(
            tenant_id=str(db_tenant_id),
            unique_rules_violated=response_payload["unique_rules_violated"],
            total_violation_occurrences=response_payload["total_violation_occurrences"],
            risk_score=response_payload["risk_score"],
            risk_tier=response_payload["risk_tier"],
            violations=violations,
            status="success",
        )

    except ValueError as val_error:
        raise HTTPException(
            status_code=400,
            detail=f"Validation error: {str(val_error)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload analysis failed: {str(e)}"
        )