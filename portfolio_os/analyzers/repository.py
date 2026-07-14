from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from portfolio_os.models import Evidence, Finding
from .base import Analyzer, AnalyzerResult, iter_files

TEXT_SUFFIXES = {".py", ".rs", ".ts", ".tsx", ".js", ".jsx", ".dart", ".go", ".java", ".kt", ".kts", ".swift", ".cs", ".cpp", ".c", ".h", ".md", ".toml", ".yaml", ".yml", ".json", ".sh", ".ps1", ".html", ".css", ".scss"}
MARKER = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[: ]?(.*)", re.IGNORECASE)


class RepositoryAnalyzer(Analyzer):
    name = "repository"

    def analyze(self, root: Path) -> AnalyzerResult:
        files = list(iter_files(root))
        suffixes = Counter(path.suffix.lower() or "<none>" for path in files)
        markers: list[dict[str, str | int]] = []
        line_count = 0
        for path in files:
            if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 1_000_000:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            line_count += len(lines)
            for index, line in enumerate(lines, 1):
                match = MARKER.search(line)
                if match and len(markers) < 250:
                    markers.append({"kind": match.group(1).upper(), "detail": match.group(2).strip()[:200], "path": path.relative_to(root).as_posix(), "line": index})

        top_dirs = sorted(path.name for path in root.iterdir() if path.is_dir() and not path.name.startswith(".") and path.name not in {"node_modules", "target", "dist", "build", "__pycache__"})
        entry_points = [name for name in ("main.py", "app.py", "cli.py", "src/main.rs", "src/lib.rs", "src/index.ts", "src/index.js", "lib/main.dart") if (root / name).exists()]
        findings: list[Finding] = []
        if len(markers) >= 25:
            evidence = tuple(Evidence(str(item["path"]), str(item["kind"]), int(item["line"])) for item in markers[:5])
            findings.append(Finding(self.name, "many-task-markers", "Many TODO/FIXME markers", "low", "high", f"Found {len(markers)} task markers in source and documentation.", "Triage markers into tracked issues and remove obsolete comments.", evidence))
        return AnalyzerResult(
            facts={"file_count": len(files), "text_line_count": line_count, "top_level_directories": top_dirs, "entry_points": entry_points, "suffix_counts": dict(suffixes.most_common(20)), "task_markers": markers},
            findings=findings,
        )
