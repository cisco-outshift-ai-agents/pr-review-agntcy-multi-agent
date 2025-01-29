from sentence_transformers import SentenceTransformer


def vector_based_similarity(value1: str, value2: str) -> float:
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    embeddings = model.encode([value1, value2])

    similarity_tensor = model.similarity(embeddings, embeddings)
    return similarity_tensor[0][1].item()
