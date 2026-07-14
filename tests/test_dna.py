from pathlib import Path

from portfolio_os.dna import DNABuilder, SimilarityEngine
from portfolio_os.engine import AnalysisEngine


def test_dna_is_deterministic() -> None:
    analysis = AnalysisEngine().analyze(Path("tests/fixtures/sample_repo"))
    builder = DNABuilder()
    first = builder.build(analysis)
    second = builder.build(analysis)
    assert first.fingerprint == second.fingerprint
    assert first.features.languages == ("python",)
    assert "testing" in first.features.capabilities


def test_identical_dna_has_full_similarity() -> None:
    analysis = AnalysisEngine().analyze(Path("tests/fixtures/sample_repo"))
    dna = DNABuilder().build(analysis)
    result = SimilarityEngine().compare(dna, dna)
    assert result.score == 1.0
    assert result.classification == "very-high-overlap"


def test_rank_is_stable_and_excludes_self_pairs() -> None:
    analysis = AnalysisEngine().analyze(Path("tests/fixtures/sample_repo"))
    dna = DNABuilder().build(analysis)
    results = SimilarityEngine().rank([dna, dna])
    assert len(results) == 1
    assert results[0].left == "sample_repo"


def test_similarity_explains_overlap() -> None:
    analysis = AnalysisEngine().analyze(Path("tests/fixtures/sample_repo"))
    dna = DNABuilder().build(analysis)
    result = SimilarityEngine().compare(dna, dna)
    assert result.reasons
    assert any("Shared" in reason for reason in result.reasons)
