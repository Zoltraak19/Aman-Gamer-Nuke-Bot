import importlib
import os
import sys
import unittest


class ConfigTokenTests(unittest.TestCase):
    def setUp(self):
        sys.modules.pop("config", None)

    def tearDown(self):
        for name in ("BOT_TOKEN", "SELF_BOT_TOKEN"):
            os.environ.pop(name, None)
        sys.modules.pop("config", None)

    def test_self_bot_token_uses_environment_variable(self):
        os.environ["SELF_BOT_TOKEN"] = "env-self-bot-token"

        config = importlib.import_module("config")

        self.assertEqual(config.SELF_BOT_TOKEN, "env-self-bot-token")

    def test_missing_environment_token_defaults_to_blank(self):
        config = importlib.import_module("config")

        self.assertEqual(config.SELF_BOT_TOKEN, "")


if __name__ == "__main__":
    unittest.main()
