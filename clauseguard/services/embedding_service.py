import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Local embedding service using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def encode(self, text: str) -> list[float]:
        """Encode a single text string into a vector."""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def encode_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Encode a batch of texts into vectors."""
        if not texts:
            return []
        embeddings = self.model.encode(
            texts, batch_size=batch_size, normalize_embeddings=True
        )
        if isinstance(embeddings, np.ndarray):
            return embeddings.tolist()
        return [e.tolist() for e in embeddings]
