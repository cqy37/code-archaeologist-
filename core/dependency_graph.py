import networkx as nx
from pathlib import Path
from typing import List, Dict, Any, Optional, Set


class DependencyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.file_index: Dict[str, Dict[str, Any]] = {}

    def add_file(self, file_info: Dict[str, Any]):
        path = file_info["file_path"]
        self.file_index[path] = file_info
        self.graph.add_node(path, **file_info)

    def add_dependency(self, from_file: str, to_file: str, dep_type: str = "import"):
        self.graph.add_edge(from_file, to_file, type=dep_type)

    def resolve_imports(self, base_dir: str):
        """Attempt to resolve relative imports to actual file paths."""
        base = Path(base_dir)
        file_names = {Path(p).name: p for p in self.file_index}

        for path, info in self.file_index.items():
            for imp in info.get("imports", []):
                # Try direct match
                if imp in file_names:
                    self.add_dependency(path, file_names[imp], "direct")
                    continue

                # Try file name match
                imp_name = imp.replace(".", "/")
                for suffix in [".py", ".js", ".java", ".ts"]:
                    candidate = imp_name + suffix
                    if candidate in file_names:
                        self.add_dependency(path, file_names[candidate], "module")
                        break

                # Try relative path resolution
                candidate_path = base / (imp.replace(".", "/") + ".py")
                if candidate_path.exists():
                    self.add_dependency(path, str(candidate_path), "resolved")

    def get_hotspots(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Files with highest in-degree + out-degree centrality."""
        if len(self.graph) == 0:
            return []

        centrality = nx.degree_centrality(self.graph)
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)

        results = []
        for path, score in sorted_nodes[:top_n]:
            in_deg = self.graph.in_degree(path)
            out_deg = self.graph.out_degree(path)
            info = self.file_index.get(path, {})
            results.append({
                "file": path,
                "centrality": round(score, 4),
                "in_degree": in_deg,
                "out_degree": out_deg,
                "lines_of_code": info.get("lines_of_code", 0),
                "functions_count": len(info.get("functions", [])),
            })
        return results

    def get_orphans(self) -> List[str]:
        """Files with no dependencies (potential dead code)."""
        orphans = []
        for node in self.graph.nodes():
            if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) == 0:
                # Only if it has no external references
                orphans.append(node)
        return orphans

    def get_upstream(self, file_path: str) -> List[str]:
        """Get all files that depend on this file."""
        try:
            return list(nx.ancestors(self.graph, file_path))
        except nx.NetworkXError:
            return []

    def get_downstream(self, file_path: str) -> List[str]:
        """Get all files this file depends on."""
        try:
            return list(nx.descendants(self.graph, file_path))
        except nx.NetworkXError:
            return []

    def find_cycles(self) -> List[List[str]]:
        """Find circular dependencies."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except Exception:
            return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [{"id": n, **self.graph.nodes[n]} for n in self.graph.nodes()],
            "edges": [{"source": u, "target": v, **d} for u, v, d in self.graph.edges(data=True)],
        }
