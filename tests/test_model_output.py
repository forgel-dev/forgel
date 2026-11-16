from __future__ import annotations

import json
import unittest

from forgel.model_output import first_object, json_objects, last_object


class ModelOutputTest(unittest.TestCase):
    def test_multiple_objects_are_all_returned(self) -> None:
        objects = json_objects('{"a": 1}{"b": 2}')
        self.assertEqual(objects, [{"a": 1}, {"b": 2}])
        self.assertEqual(first_object('{"a": 1}{"b": 2}'), {"a": 1})
        self.assertEqual(last_object('{"a": 1}{"b": 2}'), {"b": 2})

    def test_an_array_is_flattened(self) -> None:
        objects = json_objects(json.dumps([{"a": 1}, {"b": 2}]))
        self.assertEqual(objects, [{"a": 1}, {"b": 2}])

    def test_text_and_code_fences_are_ignored(self) -> None:
        raw = 'Here is the result:\n```json\n{"a": 1}\n```\n'
        self.assertEqual(json_objects(raw), [{"a": 1}])
        fenced = '```JSON\n{"a": 1}\n```'
        self.assertEqual(json_objects(fenced), [{"a": 1}])

    def test_invalid_output_has_no_objects(self) -> None:
        self.assertEqual(json_objects("not json"), [])
        self.assertIsNone(last_object("not json"))


if __name__ == "__main__":
    unittest.main()
