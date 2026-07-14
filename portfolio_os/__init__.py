"""Portfolio OS: evidence-based repository analysis and governance."""

from portfolio_os.git_auth import configure_git_auth

configure_git_auth()

from portfolio_os.config import PortfolioConfig, load_runtime_config
from portfolio_os.dashboard import DashboardResult, PortfolioDashboard
from portfolio_os.dna import DNABuilder, SimilarityEngine
from portfolio_os.engine import AnalysisEngine
from portfolio_os.graph import GraphBuilder, GraphQuery, GraphStore, KnowledgeGraph
from portfolio_os.history import PortfolioHistory, SnapshotResult
from portfolio_os.operations import LockStatus, RefreshOperations
from portfolio_os.pipeline import PipelineResult, PipelineStageResult, PolicyGateError, PortfolioPipeline
from portfolio_os.plugins import PluginRegistry
from portfolio_os.policy import PolicyResult, PolicyViolation, PortfolioPolicy
from portfolio_os.portfolio import PortfolioBuildResult, PortfolioBuilder
from portfolio_os.sync import GitHubAPIClient, SubprocessGitClient, WorkspaceSynchronizer
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
]
__version__ = "1.0.0"
