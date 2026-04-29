import os
from pathlib import Path
from typing import List, Dict, Any
from core.code_parser import CodeParser
from core.dependency_graph import DependencyGraph
from core.knowledge_base import KnowledgeBase


class ExplorerAgent:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.parser = CodeParser()
        self.max_files = self.config.get("max_files", 1000)
        self.include_patterns = self.config.get("include_patterns", ["*.py", "*.js", "*.java", "*.sql"])
        self.exclude_patterns = self.config.get("exclude_patterns", ["node_modules", ".git", "__pycache__"])

    def explore(self, directory: str, kb: KnowledgeBase, graph: DependencyGraph) -> Dict[str, Any]:
        files = self._scan_directory(directory)
        parsed_files = []

        for fp in files:
            info = self.parser.parse_file(fp)
            if "error" not in info:
                kb.store_file(info)
                graph.add_file(info)
                parsed_files.append(info)

        graph.resolve_imports(directory)

        # Store edges in KB
        for u, v, d in graph.graph.edges(data=True):
            kb.store_edge(u, v, d.get("type", "import"))

        hotspots = graph.get_hotspots(top_n=10)
        orphans = graph.get_orphans()
        cycles = graph.find_cycles()

        # Store findings
        for h in hotspots:
            kb.store_finding(
                h["file"], "explorer", "hotspot",
                f"High centrality file (score={h['centrality']}), {h['in_degree']} inbound, {h['out_degree']} outbound deps",
                confidence=0.95
            )

        for o in orphans:
            kb.store_finding(
                o, "explorer", "orphan",
                "File has no detected dependencies — potential dead code or standalone utility",
                confidence=0.7
            )

        for c in cycles:
            cycle_str = " -> ".join([Path(p).name for p in c])
            kb.store_finding(
                c[0], "explorer", "circular_dependency",
                f"Circular dependency detected: {cycle_str}",
                confidence=0.9
            )

        return {
            "total_files": len(files),
            "parsed_files": len(parsed_files),
            "hotspots": hotspots,
            "orphans": orphans,
            "cycles": cycles,
        }

    def _scan_directory(self, directory: str) -> List[str]:
        files = []
        root = Path(directory)

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if self._should_exclude(path):
                continue
            if not self._should_include(path):
                continue
            files.append(str(path.resolve()))
            if len(files) >= self.max_files:
                break

        return files

    def _should_exclude(self, path: Path) -> bool:
        parts = path.parts
        for pattern in self.exclude_patterns:
            if pattern in parts or path.match(pattern):
                return True
        return False

    def _should_include(self, path: Path) -> bool:
        for pattern in self.include_patterns:
            if path.match(pattern):
                return True
        return False
