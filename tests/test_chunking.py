import unittest

from retrieval_research.chunking import chunk_document
from retrieval_research.schema import Document, Page


class ChunkingTest(unittest.TestCase):
    def test_chunks_created_for_simple_text(self):
        doc = Document(
            id="test",
            source_path="test.md",
            title="Test",
            pages=[Page(id="p1", number=1, text="# Header\n\nSome content here for testing.")],
        )
        chunks = chunk_document(doc, max_words=10, overlap_words=2)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0].document_id, "test")

    def test_chunks_respect_max_words(self):
        doc = Document(
            id="test",
            source_path="test.md",
            title="Test",
            pages=[Page(id="p1", number=1, text="word " * 50)],
        )
        chunks = chunk_document(doc, max_words=10, overlap_words=2)
        self.assertGreaterEqual(len(chunks), 5)

    def test_chunks_preserve_section_from_headings(self):
        doc = Document(
            id="test",
            source_path="test.md",
            title="Test",
            pages=[
                Page(
                    id="p1",
                    number=1,
                    text="# Alpha\n\nAlpha content.\n\n# Beta\n\nBeta content.",
                )
            ],
        )
        chunks = chunk_document(doc, max_words=20, overlap_words=0)
        sections = {chunk.parent_section for chunk in chunks}
        self.assertIn("Alpha", sections)
        self.assertIn("Beta", sections)

    def test_chunks_empty_page_skipped(self):
        doc = Document(
            id="test",
            source_path="test.md",
            title="Test",
            pages=[Page(id="p1", number=1, text="")],
        )
        chunks = chunk_document(doc, max_words=10, overlap_words=2)
        self.assertEqual(len(chunks), 0)

    def test_chunks_use_config_defaults_when_no_args(self):
        doc = Document(
            id="test",
            source_path="test.md",
            title="Test",
            pages=[Page(id="p1", number=1, text="word " * 500)],
        )
        chunks = chunk_document(doc)
        self.assertGreaterEqual(len(chunks), 2)
        for chunk in chunks:
            self.assertIsNotNone(chunk.chunk_index)

    def test_chunk_metadata_contains_source_page_id(self):
        doc = Document(
            id="test",
            source_path="test.md",
            title="Test",
            pages=[Page(id="p1", number=1, text="Some content.")],
        )
        chunks = chunk_document(doc, max_words=10, overlap_words=0)
        self.assertEqual(chunks[0].metadata.get("source_page_id"), "p1")


if __name__ == "__main__":
    unittest.main()
