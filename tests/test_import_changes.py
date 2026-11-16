import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "import_changes.py"
spec = importlib.util.spec_from_file_location("import_changes", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ChangeParserTests(unittest.TestCase):
    def setUp(self):
        self.html = """<html><body><nav>Menu</nav><main>
        <h1>Zmiany do planu</h1><h3>2026-11-17 uploading 75%</h3>
        <h4>1B</h4>
        <p>Osoby nieuczęszczające na religię zwolnione do domu po lekcji 7</p>
        <p>Lekcja 8 grupa religia – zajęcia z bibliotekarzem p. Strzelec s. biblioteka</p>
        <h4>4B</h4>
        <p>Lekcja 4, 5 grupa 1 – zastępstwo tworzenie p. Ferdyn s. 6A</p>
        <h4>4D</h4><p>Klasa zwolniona do domu po lekcji 7</p>
        </main><footer>Stopka</footer></body></html>"""

    def test_date_and_original_text_are_preserved(self):
        date, title, messages = module.parse_messages(self.html)
        self.assertEqual(date, "2026-11-17")
        self.assertIn("uploading 75%", title)
        self.assertIn("po lekcji 7", messages[0]["raw_text"])

    def test_class_wide_release_is_not_misread_as_a_lesson(self):
        _, _, messages = module.parse_messages(self.html)
        self.assertEqual(messages[0]["class_name"], "1B")
        self.assertEqual(messages[0]["lesson_numbers"], [])
        self.assertEqual(messages[0]["scope"], "class")

    def test_specific_lesson_fields_are_extracted(self):
        _, _, messages = module.parse_messages(self.html)
        item = messages[2]
        self.assertEqual(item["class_name"], "4B")
        self.assertEqual(item["lesson_numbers"], [4, 5])
        self.assertEqual(item["group"], "1")
        self.assertEqual(item["teacher"], "Ferdyn")
        self.assertEqual(item["room"], "6A")

    def test_teacher_and_room_not_confused(self):
        _, _, messages = module.parse_messages(self.html)
        item = messages[1]
        self.assertEqual(item["teacher"], "Strzelec")
        self.assertEqual(item["room"], "biblioteka")


if __name__ == "__main__":
    unittest.main()
