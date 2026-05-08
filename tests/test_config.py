import os
import unittest

from retrieval_research.config import get_settings, reset_settings_cache_for_tests


class ConfigTest(unittest.TestCase):
    def setUp(self):
        reset_settings_cache_for_tests()

    def tearDown(self):
        reset_settings_cache_for_tests()

    def test_defaults_apply_when_no_env_vars(self):
        settings = get_settings()
        self.assertEqual(settings.data_root, "data")
        self.assertEqual(settings.gemini_model, "gemini-3.1-pro-preview")
        self.assertEqual(settings.default_chunk_max_words, 220)
        self.assertEqual(settings.default_chunk_overlap_words, 40)
        self.assertEqual(settings.default_bm25_k1, 1.5)
        self.assertEqual(settings.default_bm25_b, 0.75)
        self.assertEqual(settings.default_dense_dimensions, 384)
        self.assertEqual(settings.default_late_dimensions, 128)
        self.assertEqual(settings.default_late_max_doc_tokens, 256)
        self.assertEqual(settings.default_visual_dimensions, 384)
        self.assertEqual(settings.default_visual_backend, "baseline")
        self.assertEqual(settings.default_visual_compression, "none")
        self.assertEqual(settings.default_colpali_model, "vidore/colpali-v1.2")
        self.assertEqual(settings.default_device, "auto")
        self.assertEqual(settings.default_top_k, 5)
        self.assertEqual(settings.default_retrieval_mode, "planner")
        self.assertEqual(settings.default_planner_merge_strategy, "score_max")
        self.assertEqual(settings.default_planner_rerank, True)
        self.assertEqual(settings.default_route_vote_bonus, 0.08)
        self.assertEqual(settings.default_rerank_overlap_weight, 0.10)
        self.assertEqual(settings.default_ocr_mode, "Hybrid")
        self.assertEqual(settings.default_dpi, 150)
        self.assertEqual(settings.ocr_min_dim, 1200)
        self.assertEqual(settings.ocr_max_dim, 2400)

    def test_env_vars_override_defaults(self):
        env_vars = {
            "RR_DATA_ROOT": "/custom/data",
            "GEMINI_MODEL": "gemini-2.0-pro",
            "RR_CHUNK_MAX_WORDS": "100",
            "RR_CHUNK_OVERLAP_WORDS": "10",
            "RR_BM25_K1": "1.2",
            "RR_BM25_B": "0.5",
            "RR_DENSE_DIMENSIONS": "256",
            "RR_LATE_DIMENSIONS": "64",
            "RR_LATE_MAX_DOC_TOKENS": "128",
            "RR_VISUAL_DIMENSIONS": "512",
            "RR_VISUAL_BACKEND": "colpali",
            "RR_VISUAL_COMPRESSION": "int8",
            "RR_COLPALI_MODEL": "vidore/colpali-v2",
            "RR_DEVICE": "mps",
            "RR_TOP_K": "10",
            "RR_RETRIEVAL_MODE": "hybrid",
            "RR_PLANNER_MERGE_STRATEGY": "route_vote",
            "RR_PLANNER_RERANK": "false",
            "RR_ROUTE_VOTE_BONUS": "0.15",
            "RR_RERANK_OVERLAP_WEIGHT": "0.25",
            "RR_OCR_MODE": "Pure Local",
            "RR_DPI": "200",
            "OCR_MIN_DIM": "800",
            "OCR_MAX_DIM": "3000",
        }
        for key, value in env_vars.items():
            os.environ[key] = value
        reset_settings_cache_for_tests()

        try:
            settings = get_settings()
            self.assertEqual(settings.data_root, "/custom/data")
            self.assertEqual(settings.gemini_model, "gemini-2.0-pro")
            self.assertEqual(settings.default_chunk_max_words, 100)
            self.assertEqual(settings.default_chunk_overlap_words, 10)
            self.assertEqual(settings.default_bm25_k1, 1.2)
            self.assertEqual(settings.default_bm25_b, 0.5)
            self.assertEqual(settings.default_dense_dimensions, 256)
            self.assertEqual(settings.default_late_dimensions, 64)
            self.assertEqual(settings.default_late_max_doc_tokens, 128)
            self.assertEqual(settings.default_visual_dimensions, 512)
            self.assertEqual(settings.default_visual_backend, "colpali")
            self.assertEqual(settings.default_visual_compression, "int8")
            self.assertEqual(settings.default_colpali_model, "vidore/colpali-v2")
            self.assertEqual(settings.default_device, "mps")
            self.assertEqual(settings.default_top_k, 10)
            self.assertEqual(settings.default_retrieval_mode, "hybrid")
            self.assertEqual(settings.default_planner_merge_strategy, "route_vote")
            self.assertEqual(settings.default_planner_rerank, False)
            self.assertEqual(settings.default_route_vote_bonus, 0.15)
            self.assertEqual(settings.default_rerank_overlap_weight, 0.25)
            self.assertEqual(settings.default_ocr_mode, "Pure Local")
            self.assertEqual(settings.default_dpi, 200)
            self.assertEqual(settings.ocr_min_dim, 800)
            self.assertEqual(settings.ocr_max_dim, 3000)
        finally:
            for key in env_vars:
                os.environ.pop(key, None)
            reset_settings_cache_for_tests()

    def test_cache_is_lru_and_clears(self):
        s1 = get_settings()
        s2 = get_settings()
        self.assertIs(s1, s2)
        reset_settings_cache_for_tests()
        s3 = get_settings()
        self.assertIsNot(s1, s3)

    def test_gemini_api_key_comes_from_env(self):
        os.environ["GEMINI_API_KEY"] = "test-key-123"
        reset_settings_cache_for_tests()
        try:
            settings = get_settings()
            self.assertEqual(settings.gemini_api_key, "test-key-123")
        finally:
            os.environ.pop("GEMINI_API_KEY", None)
            reset_settings_cache_for_tests()


if __name__ == "__main__":
    unittest.main()
