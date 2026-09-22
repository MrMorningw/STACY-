import unittest
from unittest.mock import patch

import voice


class VoiceTests(unittest.TestCase):
    @patch("voice.shutil.which", return_value=None)
    def test_voice_is_optional(self, _):
        self.assertFalse(voice.disponivel())
        with self.assertRaises(RuntimeError):
            voice.ouvir()

    @patch("voice.shutil.which", return_value=None)
    def test_tts_falls_back_without_dependency(self, _):
        self.assertFalse(voice.falar("teste"))

if __name__ == "__main__":
    unittest.main()
