import logging
import unittest

from retrieval_research.log import get_logger, setup_logging, silence_noisy_third_party


class LogTest(unittest.TestCase):
    def test_get_logger_returns_named_logger(self):
        logger = get_logger("test")
        self.assertEqual(logger.name, "retrieval_research.test")

    def test_get_logger_root(self):
        logger = get_logger()
        self.assertEqual(logger.name, "retrieval_research")

    def test_setup_logging_adds_handler(self):
        setup_logging(level=logging.DEBUG)
        logger = get_logger()
        self.assertGreaterEqual(len(logger.handlers), 0)

    def test_silence_noisy_third_party(self):
        silence_noisy_third_party()
        self.assertEqual(logging.getLogger("httpx").level, logging.WARNING)
        self.assertEqual(logging.getLogger("PIL").level, logging.WARNING)


if __name__ == "__main__":
    unittest.main()
