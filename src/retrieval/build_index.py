import json
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from src.config import (
    EMBEDDING_MODEL,
    tenant_redacted_dir,
    tenant_index_path,
    tenant_index_meta_path
)

# Load model once — frozen, inference only, no training
print(f"[INDEX] Loading embedding model: {EMBEDDING_MODEL}")
model = SentenceTransformer(EMBEDDING_MODEL)
model.eval()

def flatten_to_text(data, path="") -> list:
    """
    Convert a nested JSON object into a list of
    readable text chunks.

    Example input:
    { "consent_flag": false, "pii_encrypted": false }

    Example output:
    ["consent_flag: false | pii_encrypted: false"]
    """
    chunks = []

    if isinstance(data, dict):
        # Collect all simple key-value pairs at this level
        text_parts = []
        for key, value in data.items():
            if not isinstance(value, (dict, list)):
                text_parts.append(f"{key}: {value}")

        # Only create a chunk if there are simple fields
        if text_parts:
            chunks.append({
                "text": " | ".join(text_parts),
                "path": path
            })

        # Recurse into nested objects
        for key, value in data.items():
            nested_path = f"{path}.{key}" if path else key
            chunks.extend(flatten_to_text(value, path=nested_path))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            chunks.extend(flatten_to_text(item, path=f"{path}[{i}]"))

    return chunks
  
def build_tenant_index(tenant_id: str):
    """
    Build a FAISS vector index for one tenant.
    Reads redacted files, embeds them, saves index.
    """
    redacted_dir = tenant_redacted_dir(tenant_id)
    index_path   = tenant_index_path(tenant_id)
    meta_path    = tenant_index_meta_path(tenant_id)

    # Create output folder if it doesn't exist
    index_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n[INDEX] Building index for: {tenant_id}")

    # ── Step 1: Load all redacted files ─────────────────
    all_chunks = []

    for json_file in sorted(redacted_dir.glob("*.json")):
        with open(json_file) as f:
            data = json.load(f)

        chunks = flatten_to_text(data)

        # Add source file name to each chunk
        for chunk in chunks:
            chunk["source_file"] = json_file.name
            chunk["tenant_id"]   = tenant_id

        all_chunks.extend(chunks)
        print(f"[INDEX]   {json_file.name} → {len(chunks)} chunks")

    if not all_chunks:
        print(f"[INDEX] ✗ No files found for {tenant_id}")
        return

    # ── Step 2: Embed all chunks ─────────────────────────
    texts = [chunk["text"] for chunk in all_chunks]
    print(f"[INDEX] Embedding {len(texts)} chunks...")

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    # ── Step 3: Build FAISS index ────────────────────────
    dimension = embeddings.shape[1]
    index     = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    # ── Step 4: Save index and metadata ──────────────────
    faiss.write_index(index, str(index_path))

    with open(meta_path, "w") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"[INDEX] ✓ {index.ntotal} vectors saved")
    print(f"[INDEX] ✓ Index  → {index_path}")
    print(f"[INDEX] ✓ Meta   → {meta_path}")
    
if __name__ == "__main__":
    print("=" * 50)
    print("BUILDING TENANT INDEXES")
    print("=" * 50)

    build_tenant_index("tenant_a")
    build_tenant_index("tenant_b")

    print("\n" + "=" * 50)
    print("ALL INDEXES BUILT SUCCESSFULLY")
    print("=" * 50)

# Save the file.

# ---

# ## What This Function Does Step by Step
# ```
# 1. Opens every JSON file in tenant's redacted folder
# 2. Converts each file to text chunks using flatten_to_text
# 3. Tags each chunk with its source file name
# 4. Embeds all chunks into vectors using the model
# 5. Builds FAISS index from those vectors
# 6. Saves two files:
#    - faiss.index  → the searchable vector database
#    - metadata.json → what each vector came from