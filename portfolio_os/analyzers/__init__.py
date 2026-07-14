from .base import Analyzer
from .documentation import DocumentationAnalyzer
from .languages import LanguageAnalyzer
from .manifests import ManifestAnalyzer
from .quality import QualityAnalyzer
from .repository import RepositoryAnalyzer
from .security import SecurityAnalyzer

DEFAULT_ANALYZERS: tuple[type[Analyzer], ...] = (
    RepositoryAnalyzer,
    LanguageAnalyzer,
    ManifestAnalyzer,
    QualityAnalyzer,
    DocumentationAnalyzer,
    SecurityAnalyzer,
)

__all__ = ["Analyzer", "DEFAULT_ANALYZERS"]
