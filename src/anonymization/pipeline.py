import json
from src.config import tenant_raw_dir

from .field_mapper import (
    map_governance_config,
    map_system_inventory,
    map_policies,
    map_customer_master,
    map_consent_records,
    map_transaction_events,
    map_access_logs,
    map_data_lifecycle,
    map_security_events,
    map_dsar_requests
)
from .db_writer import write_tenant_data

def run_anonymization_pipeline(tenant_id: str) -> dict:
    """
    Orchestrates the full anonymization pipeline.
    
    1. Loads raw JSON format.
    2. Applies field dropping logic via Gate 1+2 validations inside mappers.
    3. Triggers anonymization techniques defined inside mappers.
    4. Writes payload via DB writer and handles PostgreSQL connections and errors.
    """
    try:
        raw_dir = tenant_raw_dir(tenant_id)
        
        pol_file = raw_dir / "policies.json"
        sys_file = raw_dir / "system_inventory.json"
        logs_file = raw_dir / "logs.json"
        
        if not pol_file.exists() or not sys_file.exists() or not logs_file.exists():
            raise FileNotFoundError(f"Missing raw JSON files for {tenant_id} at {raw_dir}")
            
        with open(pol_file, "r") as f:
            policies_raw = json.load(f)
        with open(sys_file, "r") as f:
            sys_inv_raw = json.load(f)
        with open(logs_file, "r") as f:
            logs_raw = json.load(f)

        mapped_data = {
            "governance_config": map_governance_config(policies_raw),
            "system_inventory": map_system_inventory(sys_inv_raw),
            "policies": map_policies(policies_raw),
            "customer_master": map_customer_master(sys_inv_raw),
            "consent_records": map_consent_records(policies_raw, sys_inv_raw),
            "transaction_events": map_transaction_events(logs_raw, policies_raw),
            "access_logs": map_access_logs(logs_raw),
            "data_lifecycle": map_data_lifecycle(sys_inv_raw),
            "security_events": map_security_events(logs_raw, policies_raw),
            "dsar_requests": map_dsar_requests(logs_raw)
        }
        
        rows_written = write_tenant_data(tenant_id, mapped_data)
        
        return {
            "tenant_id": tenant_id,
            "tables_written": 10,
            "rows_written": rows_written,
            "status": "success"
        }
        
    except FileNotFoundError as e:
        return {"tenant_id": tenant_id, "status": "error", "message": str(e)}
    except Exception as e:
        return {"tenant_id": tenant_id, "status": "error", "message": f"Database or mapping error: {str(e)}"}

if __name__ == "__main__":
    import sys
    import json
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else "tenant_a"
    result = run_anonymization_pipeline(tenant_id)
    print(json.dumps(result, indent=2))
