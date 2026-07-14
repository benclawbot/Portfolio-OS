"""Portfolio OS: evidence-based repository analysis and governance."""

from portfolio_os.git_auth import configure_git_auth

configure_git_auth()

from portfolio_os.config import PortfolioConfig, load_runtime_config
from portfolio_os.dna import DNABuilder, SimilarityEngine
from portfolio_os.engine import AnalysisEngine
from portfolio_os.graph import GraphBuilder, GraphQuery, GraphStore, KnowledgeGraph
from portfolio_os.plugins import PluginRegistry
from portfolio_os.sync import GitHubAPIClient, SubprocessGitClient, WorkspaceSynchronizer

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
]
__version__ = "0.7.0"
