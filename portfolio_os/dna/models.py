from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DNAFeatureSet:
    languages: tuple[str, ...] = ()
    ecosystems: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    directories: tuple[str, ...] = ()
    entry_points: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, list[str]]:
        return {key: list(value) for key, value in asdict(self).items()}


@dataclass(frozen=True)
class RepositoryDNA:
    repository: str
    fingerprint: str
    features: DNAFeatureSet
    weights: dict[str, float]
    evidence_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "fingerprint": self.fingerprint,
            "features": self.features.to_dict(),
            "weights": dict(self.weights),
            "evidence_count": self.evidence_count,
        }


@dataclass(frozen=True)
class SimilarityDimension:
    name: str
    score: float
    weight: float
    overlap: tuple[str, ...] = ()
    left_only: tuple[str, ...] = ()
    right_only: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 4),
            "weight": self.weight,
            "overlap": list(self.overlap),
            "left_only": list(self.left_only),
            "right_only": list(self.right_only),
        }


@dataclass(frozen=True)
class RepositorySimilarity:
    left: str
    right: str
    score: float
    classification: str
    dimensions: tuple[SimilarityDimension, ...] = ()
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "right": self.right,
            "score": round(self.score, 4),
            "classification": self.classification,
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
            "reasons": list(self.reasons),
        }
