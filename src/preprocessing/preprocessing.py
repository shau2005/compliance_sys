"""
preprocessing/preprocessing.py
================================
DPDP Compliance Checker — Data Preprocessing Pipeline

Responsibilities:
    1. Accept 10 raw CSV files from the frontend
    2. Apply Gate 1 + Gate 2 field selection (design-time, from field_config.json)
    3. Apply Gate 3 calibration if needed (--calibrate flag)
    4. Write 10 CSV files with selected fields to output directory
    5. Pass selected-field CSVs to anonymization/csv_loader.py for redaction

Usage:
    Normal preprocessing run (Gate 1 + Gate 2 field selection):
        python preprocessing.py --input-dir raw/ --output-dir selected/

    Gate 3 calibration (run once after pilot violations are generated):
        python preprocessing.py --calibrate \
            --input-dir selected/ \
            --violations violations_output.csv

The field_config.json in the same directory as this file controls all
field selection decisions. Do not hardcode field names here.
"""

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Optional
import io

import numpy as np
import pandas as pd
from scipy.stats import pointbiserialr
from sklearn.preprocessing import LabelEncoder

# ── PATHS ─────────────────────────────────────────────────────────────────────

HERE        = Path(__file__).parent
CONFIG_PATH = HERE / "field_config.json"

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

# Expected input files from the frontend (table_name -> filename)
EXPECTED_FILES: Dict[str, str] = {
    "governance_config":  "governance_config.csv",
    "customer_master":    "customer_master.csv",
    "consent_records":    "consent_records.csv",
    "transaction_events": "transaction_events.csv",
    "access_logs":        "access_logs.csv",
    "data_lifecycle":     "data_lifecycle.csv",
    "security_events":    "security_events.csv",
    "dsar_requests":      "dsar_requests.csv",
    "system_inventory":   "system_inventory.csv",
    "policies":           "policies.csv",
}

# Gate 3 correlation threshold
GATE3_THRESHOLD = 0.15

# Table primary keys (used by Gate 3 label joining)
TABLE_PKS = {
    "customer_master":    "customer_id",
    "consent_records":    "consent_id",
    "transaction_events": "event_id",
    "access_logs":        "access_id",
    "data_lifecycle":     "lifecycle_id",
    "security_events":    "security_id",
    "dsar_requests":      "dsar_id",
    "governance_config":  "tenant_id",
    "system_inventory":   "system_id",
    "policies":           "policy_id",
}

# ── LOGGING ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("preprocessing")



# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — API WRAPPER FUNCTION (for in-memory processing)
# ═══════════════════════════════════════════════════════════════════════════════

def process_uploaded_files(
    uploaded_files: Dict[str, bytes],
    tenant_id: str
) -> Dict[str, pd.DataFrame]:
    """
    API wrapper for in-memory CSV processing (no file I/O).
    
    Accepts raw CSV data as bytes, applies Gate 1 + Gate 2 field selection,
    returns selected-field dataframes ready for anonymization.
    
    Args:
        uploaded_files: Dict mapping file_key to raw CSV bytes
                       Keys: governance_config, customer_master, consent_records, etc.
        tenant_id: Tenant identifier for field selection
    
    Returns:
        Dict[str, pd.DataFrame]: Selected-field dataframes
        
    Raises:
        ValueError: If validation fails
    """
    config = load_config()
    
    expected_files = list(EXPECTED_FILES.keys())
    
    # Validate all files are provided
    missing_files = [f for f in expected_files if f not in uploaded_files or uploaded_files[f] is None]
    if missing_files:
        raise ValueError(f"Missing required files: {', '.join(missing_files)}")
    
    selected_tables = {}
    
    for table_name in expected_files:
        csv_bytes = uploaded_files[table_name]
        
        # Load CSV from bytes
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes), dtype=str, keep_default_na=False)
        except Exception as e:
            raise ValueError(f"Failed to parse {table_name} CSV: {str(e)}")
        
        if df.empty:
            raise ValueError(f"{table_name} CSV is empty")
        
        # Filter by tenant_id
        if "tenant_id" not in df.columns:
            raise ValueError(f"{table_name} missing required 'tenant_id' column")
        
        df = df[df["tenant_id"] == tenant_id].copy()
        
        if df.empty:
            raise ValueError(f"No data found in {table_name} for tenant_id={tenant_id}")
        
        # Check table is in config
        if table_name not in config:
            raise ValueError(f"{table_name} not found in field_config.json")
        
        # Apply gate field selection
        selected_df = preprocess_table(df, table_name, config[table_name])
        selected_tables[table_name] = selected_df
    
    return selected_tables

def load_config() -> dict:
    """Load and validate field_config.json."""
    if not CONFIG_PATH.exists():
        log.error(f"field_config.json not found at {CONFIG_PATH}")
        sys.exit(1)
    config = json.loads(CONFIG_PATH.read_text())
    log.info(f"Loaded field_config.json — {len([k for k in config if not k.startswith('_')])} tables configured")
    return config


def get_tenant_id(df: pd.DataFrame, table_name: str) -> str:
    """Extract tenant_id from the dataframe for use in field selection."""
    if "tenant_id" in df.columns and len(df) > 0:
        return str(df["tenant_id"].iloc[0])
    return "UNKNOWN"


def select_fields(
    series: pd.Series,
    field: str,
    meta: dict,
) -> Optional[pd.Series]:
    """
    Apply Gate 1, 2 field selection decision based on field_config.json.
    
    Returns:
        pd.Series with values — if field should be kept
        None                   — if field should be dropped
    """
    action = meta.get("action", "DROP")

    # ── DROP ────────────────────────────────────────────────────────────────
    # Gate 1 failed or Gate 2 failed — field will be dropped
    if action == "DROP":
        return None

    # ── GATE_3_CANDIDATE ────────────────────────────────────────────────────
    # Field is pending Gate 3 evaluation. Keep during pilot phase.
    # After Gate 3 runs, this entry will be updated to KEEP or DROP.
    if action == "GATE_3_CANDIDATE":
        log.debug(f"  {field}: GATE_3_CANDIDATE — keeping for pilot evaluation")
        return series.copy()

    # ── KEEP ────────────────────────────────────────────────────────────────
    # Field passes Gate 1 and Gate 2 — keep as-is for anonymization
    if action == "KEEP":
        return series.copy()

    log.warning(f"  Unknown action '{action}' for field {field} — dropping for safety")
    return None


def preprocess_table(
    df: pd.DataFrame,
    table_name: str,
    table_config: dict,
) -> pd.DataFrame:
    """
    Apply Gate 1 + Gate 2 field selection to one table.
    
    Process:
        For each field in table_config:
            - If field exists in df and action is KEEP or GATE_3_CANDIDATE: keep it
            - If field exists in df and action is DROP: drop it
            - If field is in df but NOT in config: drop it (unknown field for safety)
            - If field is in config but NOT in df: skip silently
    
    Returns a new DataFrame with only the selected fields (no redaction applied).
    """
    tenant_id = get_tenant_id(df, table_name)
    result_cols = {}

    # Fields defined in config
    for field, meta in table_config.items():
        if field not in df.columns:
            # Field in config but not in CSV — skip silently (may be a dropped legacy field)
            continue

        selected = select_fields(df[field], field, meta)

        if selected is None:
            # Gate decision: DROP
            log.debug(f"  {table_name}.{field}: DROPPED (gate={meta.get('gate')})")
            continue

        # Keep original field name (no redaction/renaming yet)
        result_cols[field] = selected

    # Warn about fields in CSV that are not in config at all
    config_fields = set(table_config.keys())
    csv_fields    = set(df.columns)
    unconfigured  = csv_fields - config_fields
    if unconfigured:
        log.warning(
            f"  {table_name}: fields in CSV not in config (dropping for safety): {unconfigured}"
        )

    return pd.DataFrame(result_cols)


def run_preprocessing(input_dir: str, output_dir: str) -> Dict[str, pd.DataFrame]:
    """
    Main Gate 1 + Gate 2 field selection pipeline.
    
    Reads each raw CSV from input_dir, applies field_config.json decisions,
    writes selected-field CSVs to output_dir.
    
    The output files keep the same names and are ready for anonymization.

    Returns dict of {table_name: selected_dataframe} for downstream use.
    """
    config     = load_config()
    input_path = Path(input_dir)
    out_path   = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("PREPROCESSING — Gate 1 + Gate 2 field selection")
    log.info("=" * 60)

    # Validate all expected files are present before processing any
    missing = []
    for table_name, filename in EXPECTED_FILES.items():
        if not (input_path / filename).exists():
            missing.append(filename)
    if missing:
        log.error(f"Missing input files: {missing}")
        log.error(f"Expected all 10 CSV files in: {input_path.resolve()}")
        sys.exit(1)

    selected_tables = {}

    for table_name, filename in EXPECTED_FILES.items():
        csv_path = input_path / filename
        log.info(f"\nProcessing: {filename}")

        # Load raw CSV
        try:
            raw_df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        except Exception as e:
            log.error(f"  Failed to read {filename}: {e}")
            sys.exit(1)

        log.info(f"  Raw: {len(raw_df)} rows, {len(raw_df.columns)} columns")

        # Check table is in config
        if table_name not in config:
            log.error(f"  {table_name} not found in field_config.json")
            sys.exit(1)

        # Apply gate field selection decisions
        selected_df = preprocess_table(raw_df, table_name, config[table_name])

        log.info(f"  Selected: {len(selected_df)} rows, {len(selected_df.columns)} columns: {list(selected_df.columns)}")

        # Write selected CSV with same name
        out_file = out_path / filename
        selected_df.to_csv(out_file, index=False)
        log.info(f"  Written: {out_file}")

        # Log gate summary for this table
        dropped = [
            f for f, m in config[table_name].items()
            if m.get("action") == "DROP" and f in raw_df.columns
        ]
        candidates = [
            f for f, m in config[table_name].items()
            if m.get("gate") == "GATE_3_CANDIDATE"
        ]
        if dropped:
            log.info(f"  Dropped fields (gate 1/2): {dropped}")
        if candidates:
            log.info(f"  Gate 3 candidates (held for pilot): {candidates}")

        selected_tables[table_name] = selected_df

    log.info("\n" + "=" * 60)
    log.info("Preprocessing complete.")
    log.info(f"Selected-field tables written to: {out_path.resolve()}")
    log.info("These files are ready for anonymization (csv_loader.py).")

    # Print summary report
    _print_summary(selected_tables, config)

    return selected_tables



def _print_summary(redacted_tables: dict, config: dict):
    """Print a gate decision summary across all tables."""
    log.info("\nFIELD SELECTION SUMMARY")
    log.info("-" * 60)

    total_raw = total_kept = total_dropped = total_candidates = 0

    for table_name, df in redacted_tables.items():
        tc = config.get(table_name, {})
        n_kept       = len(df.columns)
        n_dropped    = sum(1 for m in tc.values() if m.get("action") == "DROP")
        n_candidates = sum(1 for m in tc.values() if m.get("gate") == "GATE_3_CANDIDATE")
        n_raw        = n_kept + n_dropped

        total_raw        += n_raw
        total_kept       += n_kept
        total_dropped    += n_dropped
        total_candidates += n_candidates

        log.info(
            f"  {table_name:<25} raw={n_raw:>3}  kept={n_kept:>3}  "
            f"dropped={n_dropped:>3}  gate3_pending={n_candidates}"
        )

    log.info("-" * 60)
    log.info(
        f"  {'TOTAL':<25} raw={total_raw:>3}  kept={total_kept:>3}  "
        f"dropped={total_dropped:>3}  gate3_pending={total_candidates}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — GATE 3 CALIBRATION
# ═══════════════════════════════════════════════════════════════════════════════
#
# This section is invoked ONLY when --calibrate is passed.
# It NEVER runs during normal preprocessing.
#
# Pre-requisites:
#   1. Pilot run completed — redacted CSVs exist in input_dir
#   2. Agent pipeline has run — violations_output.csv exists
#      Required columns: record_id, table_name, violation_flag (0 or 1)
#
# What it does:
#   1. Finds all GATE_3_CANDIDATE fields in field_config.json
#   2. Loads redacted table data + violation labels
#   3. Computes point-biserial correlation per candidate field
#   4. Updates field_config.json: KEEP if |corr| >= threshold, else DROP
#   5. Sets _meta.gate3_status = COMPLETE
#
# After this runs:
#   All GATE_3_CANDIDATE entries are resolved to GATE_3_KEEP or GATE_3_DROP.
#   Normal preprocessing runs will now apply those decisions automatically.
# ─────────────────────────────────────────────────────────────────────────────

def _compute_correlation(series: pd.Series, violation_flag: pd.Series) -> float:
    """
    Compute absolute point-biserial correlation between a feature and violation_flag.
    Handles numeric and categorical (string/enum) fields.
    Returns float in [0, 1]. Returns 0.0 if correlation is undefined.
    """
    x = series.copy()

    # Encode categorical/string fields
    if x.dtype == object or str(x.dtype).startswith("category"):
        x = LabelEncoder().fit_transform(x.astype(str).fillna("__missing__"))
        x = pd.Series(x)
    else:
        x = pd.to_numeric(x, errors="coerce")
        x = x.fillna(x.median() if not x.isna().all() else 0)

    y = violation_flag.astype(int)

    # Correlation is undefined if either array has no variance
    if float(np.std(np.array(x))) == 0 or float(np.std(y.values)) == 0:
        return 0.0

    corr, _ = pointbiserialr(np.array(x), y.values)
    return abs(float(corr))


def _load_violation_flags(
    violations_path: str,
    table_df: pd.DataFrame,
    table_name: str,
) -> Optional[pd.Series]:
    """
    Join violation_flag labels onto the rows of a redacted table.

    violations_output.csv format:
        record_id   — matches the redacted PK of the table row
        table_name  — which table this violation came from
        violation_flag — 0 (compliant) or 1 (violation)

    Returns a pd.Series of violation_flag values aligned to table_df rows,
    or None if no labels found for this table.
    """
    violations_df = pd.read_csv(violations_path, dtype=str)

    required = {"record_id", "table_name", "violation_flag"}
    if not required.issubset(violations_df.columns):
        log.error(f"violations file missing columns: {required - set(violations_df.columns)}")
        sys.exit(1)

    pk = TABLE_PKS.get(table_name)
    if not pk or pk not in table_df.columns:
        log.warning(f"  No PK found for {table_name} — skipping")
        return None

    table_violations = violations_df[
        violations_df["table_name"] == table_name
    ][["record_id", "violation_flag"]].copy()

    if table_violations.empty:
        log.warning(f"  No violation labels found for {table_name} in violations file")
        return None

    merged = table_df[[pk]].merge(
        table_violations,
        left_on=pk,
        right_on="record_id",
        how="left",
    )
    merged["violation_flag"] = merged["violation_flag"].fillna(0).astype(int)
    return merged["violation_flag"]


def run_gate3_calibration(
    input_dir: str,
    violations_path: str,
    threshold: float = GATE3_THRESHOLD,
):
    """
    Gate 3 calibration — run once after pilot.

    Loads GATE_3_CANDIDATE fields from selected-field tables, computes correlation
    against violation labels, updates field_config.json with final decisions.
    """
    config = load_config()

    # ── Guard: check gate3 hasn't already run ────────────────────
    if config["_meta"].get("gate3_status") == "COMPLETE":
        log.warning("Gate 3 has already been run on this config.")
        log.warning(f"  Previous run date: {config['_meta'].get('gate3_run_date')}")
        confirm = input("Re-run Gate 3 and overwrite previous decisions? [y/N]: ").strip().lower()
        if confirm != "y":
            log.info("Aborted. field_config.json unchanged.")
            return

    # ── Check violations file exists ─────────────────────────────
    if not os.path.exists(violations_path):
        log.error(f"Violations file not found: {violations_path}")
        log.error("Run the agent pipeline first to generate violation labels.")
        sys.exit(1)

    input_path = Path(input_dir)

    log.info("=" * 60)
    log.info("GATE 3 CALIBRATION")
    log.info(f"Correlation threshold: {threshold}")
    log.info("=" * 60)

    # ── Find all candidates ───────────────────────────────────────
    candidates = {}
    for table_name, table_config in config.items():
        if table_name.startswith("_"):
            continue
        fields = [
            f for f, m in table_config.items()
            if m.get("gate") == "GATE_3_CANDIDATE"
        ]
        if fields:
            candidates[table_name] = fields

    if not candidates:
        log.info("No GATE_3_CANDIDATE fields found. Nothing to calibrate.")
        return

    log.info(f"\nCandidates found:")
    for t, fields in candidates.items():
        log.info(f"  {t}: {fields}")

    # ── Process each table ────────────────────────────────────────
    results = []

    for table_name, field_list in candidates.items():
        csv_path = input_path / EXPECTED_FILES[table_name]
        if not csv_path.exists():
            log.warning(f"\n{table_name}.csv not found in {input_dir} — skipping")
            continue

        log.info(f"\nTable: {table_name}")

        table_df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        log.info(f"  Rows: {len(table_df)}")

        # Get violation flags for this table
        flags = _load_violation_flags(violations_path, table_df, table_name)
        if flags is None:
            # No labels — mark all candidates as DROP
            log.warning(f"  No labels available — marking all candidates as DROP")
            for field in field_list:
                _apply_gate3_decision(config, table_name, field, 0.0, "DROP",
                                      note="No violation labels available for this table")
                results.append((table_name, field, 0.0, "DROP"))
            continue

        violation_rate = flags.mean()
        log.info(f"  Violation rate: {violation_rate:.1%}")

        # Cannot compute correlation if violation_flag has no variance
        if violation_rate == 0.0 or violation_rate == 1.0:
            log.warning(f"  No variance in violation_flag — correlation undefined")
            log.warning(f"  All candidates in {table_name} marked as DROP")
            for field in field_list:
                _apply_gate3_decision(config, table_name, field, 0.0, "DROP",
                                      note="No variance in violation_flag during pilot run")
                results.append((table_name, field, 0.0, "DROP"))
            continue

        # Compute correlation for each candidate field
        for field in field_list:
            # Field names are kept as-is (no renaming)
            col_name = field

            if col_name not in table_df.columns:
                log.warning(f"  {field}: not found in CSV — skipping")
                continue

            corr     = _compute_correlation(table_df[col_name], flags)
            decision = "KEEP" if corr >= threshold else "DROP"

            _apply_gate3_decision(config, table_name, field, corr, decision, note=None)
            results.append((table_name, field, corr, decision))

            status = "KEEP ✓" if decision == "KEEP" else "DROP ✗"
            log.info(
                f"  {field:<30} |corr|={corr:.4f}  threshold={threshold}  → {status}"
            )

    # ── Final summary ─────────────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info("GATE 3 RESULTS")
    log.info("=" * 60)

    kept    = [(t, f, c) for t, f, c, d in results if d == "KEEP"]
    dropped = [(t, f, c) for t, f, c, d in results if d == "DROP"]

    if kept:
        log.info(f"\nKEPT — {len(kept)} field(s) (above threshold {threshold}):")
        for t, f, c in kept:
            log.info(f"  {t}.{f}  |corr|={c:.4f}")

    if dropped:
        log.info(f"\nDROPPED — {len(dropped)} field(s) (below threshold {threshold}):")
        for t, f, c in dropped:
            log.info(f"  {t}.{f}  |corr|={c:.4f}")

    # ── Update meta and write config ──────────────────────────────
    config["_meta"]["gate3_status"]    = "COMPLETE"
    config["_meta"]["gate3_run_date"]  = str(date.today())
    config["_meta"]["gate3_threshold"] = threshold

    CONFIG_PATH.write_text(json.dumps(config, indent=2))

    log.info(f"\nfield_config.json updated.")
    log.info("Gate 3 complete. All GATE_3_CANDIDATE fields are now resolved.")
    log.info("On all future preprocessing runs, Gate 3 decisions are applied automatically.")
    log.info("To re-run Gate 3, call: python preprocessing.py --calibrate --violations <file>")


def _apply_gate3_decision(
    config: dict,
    table_name: str,
    field: str,
    corr: float,
    decision: str,
    note: Optional[str],
):
    """Write Gate 3 decision into the config dict for a single field."""
    meta = config[table_name][field]
    meta["gate"]               = "GATE_3"
    meta["gate3_result"]       = decision
    meta["gate3_correlation"]  = round(corr, 4)
    meta["gate3_decided_on"]   = str(date.today())
    meta["action"]             = decision   # this is what preprocess_table() reads
    if note:
        meta["gate3_note"] = note


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="DPDP preprocessing pipeline — Gate 1, 2, 3 field selection"
    )

    # ── Normal run ────────────────────────────────────────────────
    parser.add_argument(
        "--input-dir",
        default="raw/",
        help="Directory containing the 10 raw CSV files from frontend (default: raw/)",
    )
    parser.add_argument(
        "--output-dir",
        default="selected/",
        help="Directory to write selected-field CSVs (default: selected/)",
    )

    # ── Gate 3 calibration ────────────────────────────────────────
    # --calibrate must be explicitly passed — Gate 3 NEVER runs automatically
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help=(
            "Run Gate 3 calibration. Requires --violations. "
            "Run ONCE after the pilot. Never runs automatically."
        ),
    )
    parser.add_argument(
        "--violations",
        default="violations_output.csv",
        help=(
            "Path to agent violations output CSV. "
            "Required columns: record_id, table_name, violation_flag. "
            "Used only with --calibrate."
        ),
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=GATE3_THRESHOLD,
        help=f"Gate 3 correlation threshold (default: {GATE3_THRESHOLD})",
    )

    args = parser.parse_args()

    if args.calibrate:
        # ── Gate 3 mode ──────────────────────────────────────────
        # input_dir here is the SELECTED-field directory (pilot output)
        # violations file has labels from agent run
        log.info("Mode: Gate 3 calibration")
        run_gate3_calibration(
            input_dir=args.input_dir,
            violations_path=args.violations,
            threshold=args.threshold,
        )
    else:
        # ── Normal preprocessing mode ─────────────────────────────
        log.info("Mode: preprocessing (Gate 1 + Gate 2)")
        run_preprocessing(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
        )


if __name__ == "__main__":
    main()
