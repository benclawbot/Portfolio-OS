from __future__ import annotations

import json
import tomllib
from pathlib import Path

from portfolio_os.models import Evidence, Finding
from .base import Analyzer, AnalyzerResult

MANIFESTS = {
    "pyproject.toml": "Python", "requirements.txt": "Python", "setup.py": "Python",
    "Cargo.toml": "Rust", "package.json": "Node.js", "go.mod": "Go",
    "pubspec.yaml": "Flutter/Dart", "pom.xml": "Maven/Java", "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle/Kotlin", "Package.swift": "Swift",
}
LOCKFILES = {"uv.lock", "poetry.lock", "Pipfile.lock", "Cargo.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "go.sum", "pubspec.lock", "Gemfile.lock", "composer.lock"}


class ManifestAnalyzer(Analyzer):
    name = "manifests"

    def analyze(self, root: Path) -> AnalyzerResult:
        found = [name for name in MANIFESTS if (root / name).exists()]
        locks = sorted(path.name for path in root.iterdir() if path.is_file() and path.name in LOCKFILES)
        dependencies: dict[str, list[str]] = {}
        frameworks: set[str] = set()
        commands: dict[str, str] = {}
        findings: list[Finding] = []

        package_json = root / "package.json"
        if package_json.exists():
            data = json.loads(package_json.read_text(encoding="utf-8"))
            dependencies["node"] = sorted(set(data.get("dependencies", {})) | set(data.get("devDependencies", {})))
            commands.update({str(k): str(v) for k, v in data.get("scripts", {}).items()})
            frameworks.update(name for name in ("next", "react", "vue", "svelte", "@angular/core", "vite", "electron", "tauri") if name in dependencies["node"])
            if not any(name in locks for name in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb")):
                findings.append(Finding(self.name, "missing-node-lockfile", "Node project has no lockfile", "medium", "high", "package.json exists but no supported Node lockfile was found.", "Commit the package-manager lockfile used by CI and releases.", (Evidence("package.json", "Node manifest detected"),)))

        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = data.get("project", {})
            dependencies["python"] = sorted(str(dep) for dep in project.get("dependencies", []))
            commands.update({str(k): str(v) for k, v in project.get("scripts", {}).items()})
            text = pyproject.read_text(encoding="utf-8").lower()
            frameworks.update(name for name in ("django", "fastapi", "flask", "streamlit", "pytest") if name in text)

        cargo = root / "Cargo.toml"
        if cargo.exists():
            data = tomllib.loads(cargo.read_text(encoding="utf-8"))
            deps = set(data.get("dependencies", {})) | set(data.get("dev-dependencies", {}))
            dependencies["rust"] = sorted(deps)
            frameworks.update(name for name in ("tokio", "axum", "actix-web", "tauri", "ratatui", "clap") if name in deps)
            if not (root / "Cargo.lock").exists() and "package" in data:
                findings.append(Finding(self.name, "missing-cargo-lockfile", "Rust application has no Cargo.lock", "low", "medium", "A Rust package manifest exists without a Cargo.lock.", "Commit Cargo.lock for applications and binaries; libraries may intentionally omit it.", (Evidence("Cargo.toml", "Rust package detected"),)))

        requirements = root / "requirements.txt"
        if requirements.exists():
            dependencies["python-requirements"] = [line.strip() for line in requirements.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]

        return AnalyzerResult(
            facts={"manifests": found, "ecosystems": sorted({MANIFESTS[name] for name in found}), "lockfiles": locks, "dependencies": dependencies, "frameworks": sorted(frameworks), "commands": commands},
            findings=findings,
        )
