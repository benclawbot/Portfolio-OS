from pathlib import Path

import pytest

from portfolio_os.models import RepositoryAnalysis
from portfolio_os.readme import GENERATED_MARKER, ReadmeGenerationError, ReadmeGenerator, extract_hero_banner


def analysis(root: Path) -> RepositoryAnalysis:
    return RepositoryAnalysis(
        repository=root.name,
        root=str(root.resolve()),
        facts={
            "repository": {"file_count": 5, "entry_points": ["src/main.py"], "top_level_directories": ["src", "tests"]},
            "languages": {"primary": "Python", "detected": ["Python"]},
            "manifests": {
                "ecosystems": ["Python"],
                "lockfiles": [],
                "frameworks": ["pytest"],
                "commands": {"sample": "sample.cli:main"},
            },
            "quality": {"test_file_count": 1, "workflows": [".github/workflows/ci.yml"]},
        },
    )


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "sample_repo"
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname="sample-tool"\nversion="1.2.3"\ndescription="Evidence based sample"\n',
        encoding="utf-8",
    )
    (root / "src/main.py").write_text("print('hello')\n", encoding="utf-8")
    return root


def test_extracts_html_hero_exactly() -> None:
    hero = '<p align="center">\n  <img src="hero.png" width="100%">\n</p>'
    readme = f"{hero}\n\n# Old title\nBody\n"
    assert extract_hero_banner(readme) == hero


def test_generator_preserves_hero_and_uses_manifest_metadata(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    hero = '<p align="center">\n  <img src="hero.png" width="100%">\n</p>'
    (root / "README.md").write_text(f"{hero}\n\n# Wrong\nAspirational feature.\n", encoding="utf-8")
    content = ReadmeGenerator().generate(root, analysis(root))
    assert content.startswith(GENERATED_MARKER)
    assert hero in content
    assert "# sample-tool" in content
    assert "Evidence based sample." in content
    assert "Aspirational feature" not in content


def test_generator_is_deterministic(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    generator = ReadmeGenerator()
    assert generator.generate(root, analysis(root)) == generator.generate(root, analysis(root))


def test_generator_refuses_failed_analysis(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    result = analysis(root)
    result.errors.append({"analyzer": "languages", "error": "boom"})
    with pytest.raises(ReadmeGenerationError, match="languages"):
        ReadmeGenerator().generate(root, result)


def test_atomic_write_and_content(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    generator = ReadmeGenerator()
    content = generator.generate(root, analysis(root))
    path = generator.write(root, content)
    assert path.read_text(encoding="utf-8") == content
    assert not list(root.glob(".README.md.*"))


def test_generated_readme_contains_only_evidence_sections(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    content = ReadmeGenerator().generate(root, analysis(root))
    assert "src/main.py" in content
    assert "python -m pip install -e ." in content
    assert "python -m pytest" in content
    assert "cloud deployment" not in content.lower()
