import unittest
from pathlib import Path

import yaml


class SemanticPolicyTest(unittest.TestCase):
    def test_semantic_rules_are_natural_language_only(self) -> None:
        policy = yaml.safe_load(
            (Path(__file__).parents[1] / "config" / "analysis-policy.yml").read_text(encoding="utf-8")
        )
        semantics = policy["semantics"]
        self.assertNotIn("checks", semantics)
        self.assertNotIn("query", semantics)
        self.assertGreaterEqual(len(semantics["instructions"]), 1)
        self.assertTrue(all(isinstance(item, str) and item.strip() for item in semantics["instructions"]))


if __name__ == "__main__":
    unittest.main()
