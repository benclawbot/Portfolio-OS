"""Portfolio OS: evidence-based repository analysis and governance."""

from portfolio_os.git_auth import configure_git_auth

configure_git_auth()

from portfolio_os.artifacts import ArtifactCatalogResult, ArtifactManager, ArtifactRecord
from portfolio_os.backlog import BacklogItem, BacklogResult, PortfolioBacklog
from portfolio_os.config import PortfolioConfig, load_runtime_config
from portfolio_os.dashboard import DashboardResult, PortfolioDashboard
from portfolio_os.dna import DNABuilder, SimilarityEngine
from portfolio_os.engine import AnalysisEngine
from portfolio_os.generators import GeneratedDocuments, PortfolioDocumentGenerator
from portfolio_os.github_index import GitHubIndexResult, GitHubMetadataIndexer
from portfolio_os.graph import GraphBuilder, GraphQuery, GraphStore, KnowledgeGraph
from portfolio_os.history import PortfolioHistory, SnapshotResult
from portfolio_os.intelligence import IntelligenceScore, RepositoryIntelligence, ScoreFactor
from portfolio_os.jobs import JobQueue, JobRecord
from portfolio_os.lineage import LineageEdge, LineageResult, RepositoryLineage
from portfolio_os.operations import LockStatus, RefreshOperations
from portfolio_os.pipeline import PipelineResult, PipelineStageResult, PolicyGateError, PortfolioPipeline
from portfolio_os.plugins import PluginRegistry
from portfolio_os.policy import PolicyResult, PolicyViolation, PortfolioPolicy
from portfolio_os.portfolio import PortfolioBuildResult, PortfolioBuilder
from portfolio_os.reuse import DuplicateGroup, DuplicateOccurrence, PortfolioReuseAnalyzer, ReuseResult
from portfolio_os.service import PortfolioHTTPServer, PortfolioService
from portfolio_os.sync import GitHubAPIClient, SubprocessGitClient, WorkspaceSynchronizer
from portfolio_os.telemetry import TelemetryReporter, TelemetryResult
from portfolio_os.trends import PortfolioTrends, TrendResult
from portfolio_os.workspace import WorkspaceCheck, WorkspaceValidation, WorkspaceValidator

__all__ = [
    "AnalysisEngine",
    "DNABuilder",
    "SimilarityEngine",
    "GraphBuilder",
    "GraphQuery",
    "GraphStore",
    "KnowledgeGraph",
    "PluginRegistry",
    "PortfolioConfig",
    "load_runtime_config",
    "GitHubAPIClient",
    "SubprocessGitClient",
    "WorkspaceSynchronizer",
    "GitHubMetadataIndexer",
    "GitHubIndexResult",
    "PortfolioBuildResult",
    "PortfolioBuilder",
    "PortfolioHistory",
    "SnapshotResult",
    "PortfolioTrends",
    "TrendResult",
    "PortfolioDashboard",
    "DashboardResult",
    "PortfolioPipeline",
    "PipelineResult",
    "PipelineStageResult",
    "PolicyGateError",
    "PortfolioPolicy",
    "PolicyResult",
    "PolicyViolation",
    "RefreshOperations",
    "LockStatus",
    "WorkspaceValidator",
    "WorkspaceValidation",
    "WorkspaceCheck",
    "RepositoryIntelligence",
    "IntelligenceScore",
    "ScoreFactor",
    "PortfolioBacklog",
    "BacklogResult",
    "BacklogItem",
    "PortfolioDocumentGenerator",
    "GeneratedDocuments",
    "JobQueue",
    "JobRecord",
    "PortfolioService",
    "PortfolioHTTPServer",
    "ArtifactManager",
    "ArtifactCatalogResult",
    "ArtifactRecord",
    "RepositoryLineage",
    "LineageResult",
    "LineageEdge",
    "PortfolioReuseAnalyzer",
    "ReuseResult",
    "DuplicateGroup",
    "DuplicateOccurrence",
    "TelemetryReporter",
    "TelemetryResult",
]
__version__ = "1.1.0"
