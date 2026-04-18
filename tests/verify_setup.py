# verify_setup.py

import sys
from pathlib import Path

print("── Checking folder structure ──")
required = [
    "data/dpdp_kb",
    "data/labels",
    "data/tenants/tenant_a/raw",
    "data/tenants/tenant_a/redacted",
    "data/tenants/tenant_b/raw",
    "data/tenants/tenant_b/redacted",
    "indexes/tenant_a",
    "indexes/tenant_b",
    "logs",
    "outputs/mappings",
    "outputs/decisions",
    "src/kb",
    "src/privacy_gateway",
    "src/retrieval",
    "src/rules_engine",
    "src/scoring",
    "src/explainability",
    "src/agent_layer",
    "src/responsible_ai",
    "src/api",
    "frontend",
    "tests",
]
all_ok = True
for folder in required:
    exists = Path(folder).exists()
    status = "✓" if exists else "✗ MISSING"
    print(f"  {status}  {folder}")
    if not exists:
        all_ok = False

print("\n── Checking key files ──")
files = [
    "data/dpdp_kb/dpdp_rules.json",
    "src/config.py",
    "requirements.txt",
    ".gitignore",
]
for f in files:
    exists = Path(f).exists()
    status = "✓" if exists else "✗ MISSING"
    print(f"  {status}  {f}")
    if not exists:
        all_ok = False

print("\n── Checking imports ──")
packages = [
    "faiss", "sentence_transformers", "fastapi",
    "streamlit", "xgboost", "shap", "pydantic", "yaml"
]
for pkg in packages:
    try:
        __import__(pkg)
        print(f"  ✓  {pkg}")
    except ImportError:
        print(f"  ✗  {pkg} — run: pip install -r requirements.txt")
        all_ok = False

print("\n── Checking config ──")
from src.config import (
    ROOT_DIR, RULES_FILE,
    EMBEDDING_MODEL, tenant_raw_dir
)
print(f"  ✓  ROOT_DIR     : {ROOT_DIR}")
print(f"  ✓  RULES_FILE   : {RULES_FILE}")
print(f"  ✓  EMBED MODEL  : {EMBEDDING_MODEL}")
print(f"  ✓  tenant_a/raw : {tenant_raw_dir('tenant_a')}")

print(f"\n{'✓ SETUP COMPLETE' if all_ok else '✗ FIX ISSUES ABOVE'}")