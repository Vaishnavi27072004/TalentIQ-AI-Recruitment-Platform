"""Natural-language candidate search using vector similarity (NOT SQL filtering).

semantic_search(query, top_k)
  What it does : finds candidates whose profile MEANS something similar to the query.
  Input        : query text, number of results.
  Output       : list of (candidate_id, similarity 0-1) sorted best first.
  How it works : embed query -> ask ChromaDB for nearest candidate vectors -> convert
                 cosine distance to similarity (1 - distance).
  Interview    : "SQLite then loads the full records for those ids, so Chroma finds,
                 SQLite supplies the data."
"""
from app.services.embedding_service import generate_embedding, get_collection, CANDIDATE_COLLECTION


def semantic_search(query: str, top_k: int = 10) -> list[tuple[int, float]]:
    collection = get_collection(CANDIDATE_COLLECTION)
    total_vectors = collection.count()
    if total_vectors == 0:
        return []
    result = collection.query(
        query_embeddings=[generate_embedding(query)],
        n_results=min(top_k, total_vectors),
        include=["distances"],
    )
    ids = result["ids"][0]
    distances = result["distances"][0]
    return [(int(candidate_id), round(1 - distance, 4)) for candidate_id, distance in zip(ids, distances)]
