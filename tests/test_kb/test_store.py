from unittest.mock import MagicMock, patch

import pytest


COLLECTION_NAMES = [
    "discovery_summaries",
    "stack_analyses",
    "use_cases",
    "competitive_intel",
    "meeting_notes",
]


@pytest.fixture
def mock_chroma_client():
    client = MagicMock()
    collections = {}
    for name in COLLECTION_NAMES:
        coll = MagicMock()
        coll.name = name
        collections[name] = coll

    def fake_get_or_create(name, embedding_function=None):
        return collections[name]

    client.get_or_create_collection = MagicMock(side_effect=fake_get_or_create)
    return client, collections


@pytest.fixture
def kb_store(mock_chroma_client, tmp_path):
    client, collections = mock_chroma_client
    with patch("src.kb.store.chromadb") as mock_chromadb:
        mock_chromadb.PersistentClient.return_value = client
        from src.kb.store import KBStore

        store = KBStore(persist_dir=str(tmp_path / "chromadb"))
    store._collections = collections
    return store


class TestKBStoreInit:
    def test_creates_persistent_client(self, tmp_path):
        with patch("src.kb.store.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.return_value = MagicMock()
            mock_chromadb.PersistentClient.return_value.get_or_create_collection = MagicMock(
                return_value=MagicMock()
            )
            from src.kb.store import KBStore

            KBStore(persist_dir=str(tmp_path / "chromadb"))
            mock_chromadb.PersistentClient.assert_called_once_with(
                path=str(tmp_path / "chromadb")
            )

    def test_creates_five_collections(self, tmp_path):
        client = MagicMock()
        client.get_or_create_collection = MagicMock(return_value=MagicMock())
        with patch("src.kb.store.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.return_value = client
            from src.kb.store import KBStore

            KBStore(persist_dir=str(tmp_path / "chromadb"))
            assert client.get_or_create_collection.call_count == 5
            created_names = {
                call.kwargs["name"]
                for call in client.get_or_create_collection.call_args_list
            }
            assert created_names == set(COLLECTION_NAMES)

    def test_collections_use_sentence_transformer_ef(self, tmp_path):
        client = MagicMock()
        client.get_or_create_collection = MagicMock(return_value=MagicMock())
        with (
            patch("src.kb.store.chromadb") as mock_chromadb,
            patch("src.kb.store.SentenceTransformerEmbeddingFunction") as mock_ef_cls,
        ):
            mock_chromadb.PersistentClient.return_value = client
            mock_ef = MagicMock()
            mock_ef_cls.return_value = mock_ef
            from src.kb.store import KBStore

            KBStore(persist_dir=str(tmp_path / "chromadb"))
            mock_ef_cls.assert_called_once_with(model_name="all-MiniLM-L6-v2")
            for call in client.get_or_create_collection.call_args_list:
                assert call.kwargs["embedding_function"] is mock_ef


class TestAddDocument:
    def test_upserts_to_correct_collection(self, kb_store):
        kb_store.add_document(
            collection_name="stack_analyses",
            doc_id="sa-001",
            text="Snowflake Enterprise on AWS",
            metadata={"customer_id": "acme", "cloud_provider": "aws"},
        )
        coll = kb_store._collections["stack_analyses"]
        coll.upsert.assert_called_once_with(
            ids=["sa-001"],
            documents=["Snowflake Enterprise on AWS"],
            metadatas=[{"customer_id": "acme", "cloud_provider": "aws"}],
        )

    def test_rejects_unknown_collection(self, kb_store):
        with pytest.raises(KeyError):
            kb_store.add_document(
                collection_name="nonexistent",
                doc_id="x",
                text="text",
                metadata={},
            )


class TestRetrieveSimilar:
    def test_queries_correct_collection(self, kb_store):
        coll = kb_store._collections["discovery_summaries"]
        coll.query.return_value = {
            "ids": [["ds-001"]],
            "documents": [["Summary for Acme"]],
            "metadatas": [[{"customer_id": "acme"}]],
            "distances": [[0.3]],
        }
        results = kb_store.retrieve_similar("discovery_summaries", "Snowflake migration")
        coll.query.assert_called_once_with(
            query_texts=["Snowflake migration"],
            n_results=5,
            where=None,
        )
        assert len(results) == 1
        assert results[0]["id"] == "ds-001"
        assert results[0]["text"] == "Summary for Acme"
        assert results[0]["metadata"] == {"customer_id": "acme"}
        assert results[0]["distance"] == 0.3

    def test_passes_metadata_filter(self, kb_store):
        coll = kb_store._collections["stack_analyses"]
        coll.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        kb_store.retrieve_similar(
            "stack_analyses",
            "AWS data stack",
            n_results=3,
            where={"cloud_provider": "aws"},
        )
        coll.query.assert_called_once_with(
            query_texts=["AWS data stack"],
            n_results=3,
            where={"cloud_provider": "aws"},
        )

    def test_returns_empty_list_for_no_results(self, kb_store):
        coll = kb_store._collections["use_cases"]
        coll.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        results = kb_store.retrieve_similar("use_cases", "streaming")
        assert results == []

    def test_rejects_unknown_collection(self, kb_store):
        with pytest.raises(KeyError):
            kb_store.retrieve_similar("nonexistent", "query")


class TestGetDocument:
    def test_retrieves_by_id(self, kb_store):
        coll = kb_store._collections["competitive_intel"]
        coll.get.return_value = {
            "ids": ["ci-001"],
            "documents": ["Snowflake vs Tower"],
            "metadatas": [{"competitor": "snowflake"}],
        }
        result = kb_store.get_document("competitive_intel", "ci-001")
        coll.get.assert_called_once_with(ids=["ci-001"])
        assert result["id"] == "ci-001"
        assert result["text"] == "Snowflake vs Tower"
        assert result["metadata"] == {"competitor": "snowflake"}

    def test_returns_none_for_missing_doc(self, kb_store):
        coll = kb_store._collections["meeting_notes"]
        coll.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        result = kb_store.get_document("meeting_notes", "missing-id")
        assert result is None


class TestGetKBStoreSingleton:
    def test_returns_same_instance(self, tmp_path):
        with (
            patch("src.kb.store.chromadb") as mock_chromadb,
            patch("src.kb.store.settings") as mock_settings,
        ):
            mock_chromadb.PersistentClient.return_value = MagicMock()
            mock_chromadb.PersistentClient.return_value.get_or_create_collection = MagicMock(
                return_value=MagicMock()
            )
            mock_settings.chromadb_dir = tmp_path / "chromadb"

            import src.kb.store as store_module

            store_module._kb_store_instance = None

            s1 = store_module.get_kb_store()
            s2 = store_module.get_kb_store()
            assert s1 is s2
            assert mock_chromadb.PersistentClient.call_count == 1
