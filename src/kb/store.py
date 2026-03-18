from __future__ import annotations

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from src.config import settings

COLLECTION_NAMES = (
    "discovery_summaries",
    "stack_analyses",
    "use_cases",
    "competitive_intel",
    "meeting_notes",
)


class KBStore:
    def __init__(self, persist_dir: str) -> None:
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self._collections: dict[str, chromadb.Collection] = {}
        for name in COLLECTION_NAMES:
            self._collections[name] = self._client.get_or_create_collection(
                name=name, embedding_function=self._ef
            )

    def add_document(
        self, collection_name: str, doc_id: str, text: str, metadata: dict
    ) -> None:
        coll = self._collections[collection_name]
        coll.upsert(ids=[doc_id], documents=[text], metadatas=[metadata])

    def retrieve_similar(
        self,
        collection_name: str,
        query: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        coll = self._collections[collection_name]
        raw = coll.query(query_texts=[query], n_results=n_results, where=where)
        results = []
        for i, doc_id in enumerate(raw["ids"][0]):
            results.append({
                "id": doc_id,
                "text": raw["documents"][0][i],
                "metadata": raw["metadatas"][0][i],
                "distance": raw["distances"][0][i],
            })
        return results

    def get_document(self, collection_name: str, doc_id: str) -> dict | None:
        coll = self._collections[collection_name]
        raw = coll.get(ids=[doc_id])
        if not raw["ids"]:
            return None
        return {
            "id": raw["ids"][0],
            "text": raw["documents"][0],
            "metadata": raw["metadatas"][0],
        }


_kb_store_instance: KBStore | None = None


def get_kb_store() -> KBStore:
    global _kb_store_instance
    if _kb_store_instance is None:
        _kb_store_instance = KBStore(persist_dir=str(settings.chromadb_dir))
    return _kb_store_instance
