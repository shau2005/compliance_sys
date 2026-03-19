import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from src.config import (
    EMBEDDING_MODEL,
    TOP_K_RETRIEVAL,
    tenant_index_path,
    tenant_index_meta_path
)

# Load model once — same model used in build_index.py
print(f"[RETRIEVE] Loading embedding model: {EMBEDDING_MODEL}")
model = SentenceTransformer(EMBEDDING_MODEL)
model.eval()

# Cache indexes in memory after first load
_index_cache = {}
_meta_cache  = {}


def _load_tenant_index(tenant_id: str):
    """
    Load FAISS index and metadata for a tenant.
    Cached after first load — not reloaded on every query.
    """
    if tenant_id not in _index_cache:
        index_path = tenant_index_path(tenant_id)
        meta_path  = tenant_index_meta_path(tenant_id)

        if not index_path.exists():
            raise FileNotFoundError(
                f"No index found for '{tenant_id}'. "
                f"Run build_index.py first."
            )

        _index_cache[tenant_id] = faiss.read_index(str(index_path))

        with open(meta_path) as f:
            _meta_cache[tenant_id] = json.load(f)

        print(f"[RETRIEVE] Loaded index for '{tenant_id}': "
              f"{_index_cache[tenant_id].ntotal} vectors")

    return _index_cache[tenant_id], _meta_cache[tenant_id]


def retrieve_evidence(
    tenant_id: str,
    query_text: str,
    top_k: int = TOP_K_RETRIEVAL
) -> list:
    """
    Search a tenant's index for evidence relevant to a query.

    Example:
        query_text = "consent required before processing personal data"
        Returns top-k evidence chunks most relevant to this query
        from that tenant's redacted files.

    ISOLATION GUARANTEE:
        Only the specified tenant's index is searched.
        tenant_a queries never touch tenant_b's index.
    """
    index, metadata = _load_tenant_index(tenant_id)

    # Embed the query — exists in RAM only, never saved anywhere
    query_vec = model.encode(
        [query_text],
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    # Search index — returns scores and positions
    scores, positions = index.search(query_vec, top_k)

    # Build results list
    results = []
    for score, pos in zip(scores[0], positions[0]):
        if pos == -1:
            continue
        result = metadata[pos].copy()
        result["relevance_score"] = round(float(score), 4)
        results.append(result)

    return results


if __name__ == "__main__":
    print("=" * 50)
    print("TESTING RETRIEVAL")
    print("=" * 50)

    # Test queries mapped to rules
    test_queries = [
        "consent required before processing personal data",
        "data retention expiry period storage limitation",
        "unauthorized employee access to personal data",
        "breach notification delay reporting",
        "encryption of sensitive personal data"
    ]

    for tenant in ["tenant_a", "tenant_b"]:
        print(f"\n── Tenant: {tenant} ──")
        for query in test_queries:
            results = retrieve_evidence(
                tenant_id=tenant,
                query_text=query,
                top_k=1
            )
            print(f"\n  Query : {query}")
            if results:
                print(f"  Match : {results[0]['text'][:100]}")
                print(f"  Score : {results[0]['relevance_score']}")
                print(f"  File  : {results[0]['source_file']}")
            else:
                print("  Match : No results found")

    print("\n" + "=" * 50)
    print("RETRIEVAL TEST COMPLETE")
    print("=" * 50)