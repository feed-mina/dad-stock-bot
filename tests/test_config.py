from pathlib import Path
import tempfile
import unittest

from dad_stock_bot.config import Settings, load_env_file


class SettingsTest(unittest.TestCase):
    def test_load_env_file_and_safe_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "KIS_ENV=demo",
                        "KIS_APP_KEY=abc",
                        "KIS_APP_SECRET=secret",
                        "DAD_STOCK_SYMBOLS=005930, 000660",
                    ]
                ),
                encoding="utf-8",
            )

            loaded = load_env_file(env_path)
            settings = Settings.from_mapping(loaded)

        self.assertEqual(settings.env, "demo")
        self.assertEqual(settings.symbols, ("005930", "000660"))
        self.assertTrue(settings.safe_summary()["has_app_key"])

    def test_invalid_env_raises(self) -> None:
        with self.assertRaises(ValueError):
            Settings.from_mapping({"KIS_ENV": "paper"})


if __name__ == "__main__":
    unittest.main()

