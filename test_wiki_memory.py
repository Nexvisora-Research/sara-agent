import shutil
import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from memory.wiki_memory import WikiMemorySystem


class WikiMemorySystemTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="sara_wiki_memory_"))
        self.memory = WikiMemorySystem(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_memory_writes_markdown_and_rebuilds_graph(self):
        record = self.memory.create_memory(
            "User owns [[Projects/Sara-Agent]] and Sara Agent is inspired by OpenHuman.",
            space="sara-agent",
            memory_type="semantic",
            title="User",
            tags=["user", "project"],
            relations=[{"predicate": "owns", "target": "Projects/Sara-Agent"}],
        )

        page = self.temp_dir / "sara-agent" / record.path
        graph = self.temp_dir / "sara-agent" / "graph" / "graph.json"

        self.assertTrue(page.exists())
        self.assertIn("[[Projects/Sara-Agent]]", page.read_text(encoding="utf-8"))
        self.assertTrue(graph.exists())
        self.assertIn("owns", graph.read_text(encoding="utf-8"))

    def test_hybrid_search_returns_explainable_results(self):
        created = self.memory.create_memory(
            "Sara Agent memory keeps Markdown as source of truth and vector databases as accelerators.",
            space="sara-agent",
            memory_type="semantic",
            title="Projects/Sara-Agent",
            tags=["architecture", "memory"],
            importance=0.9,
        )

        results = self.memory.search_memory("Markdown vector source truth", space="sara-agent")

        self.assertTrue(results)
        self.assertIn(created.id, {result.record.id for result in results})
        self.assertTrue(results[0].reasons)
        self.assertGreater(results[0].score, 0.5)

    def test_consolidation_creates_episode_fact_and_reflection(self):
        outcome = self.memory.consolidate_memory(
            space="riva",
            short_term_events=[
                {
                    "summary": "Decision: RIVA uses Sara Agent memory. User prefers human editable Markdown.",
                    "participants": ["user", "Sara"],
                    "tags": ["decision", "preference"],
                    "importance": 0.82,
                }
            ],
        )

        self.assertTrue(outcome["created_memory_ids"])
        self.assertIsNotNone(outcome["reflection_id"])
        self.assertTrue((self.temp_dir / "riva" / "reflections").exists())
        results = self.memory.search_memory("human editable Markdown", space="riva")
        self.assertTrue(results)

    def test_update_and_delete_memory_keep_indexes_in_sync(self):
        record = self.memory.create_memory("Tunify related to Sara Agent.", space="tunify", title="Projects/Tunify")
        updated = self.memory.update_memory(record.id, space="tunify", content="Tunify uses [[Sara Agent]] memory.")

        self.assertIn("Tunify uses", updated.content)
        self.assertTrue(self.memory.search_memory("Tunify uses", space="tunify"))

        self.assertTrue(self.memory.delete_memory(record.id, space="tunify"))
        self.assertFalse(self.memory.search_memory("Tunify uses", space="tunify"))

    def test_default_root_uses_sara_home_memories_wiki(self):
        sara_home = self.temp_dir / "profile-home"
        with patch.dict(os.environ, {"sara_HOME": str(sara_home), "SARA_MEMORY_ROOT": ""}):
            memory = WikiMemorySystem()

        self.assertEqual(memory.root, sara_home / "memories" / "wiki")


if __name__ == "__main__":
    unittest.main()
