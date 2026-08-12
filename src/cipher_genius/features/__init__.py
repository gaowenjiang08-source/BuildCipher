"""
BuildTrust Features Package
高级功能模块 - 完整版 v3.0
"""

# Core Features (v2.0)
from .scheme_comparator import SchemeComparator, ComparisonMetrics
from .security_assessor import SecurityAssessor, ThreatLevel
from .recommender import ComponentRecommender, PerformanceLevel, UseCaseCategory
from .performance_estimator import PerformanceEstimator, Platform
from .exporter import SchemeExporter
from .tutorials import TutorialManager, Tutorial

# Enhanced tutorials (v3.0)
try:
    from .tutorials_enhanced import EnhancedTutorialManager, TutorialStep
    ENHANCED_TUTORIALS_AVAILABLE = True
except ImportError:
    ENHANCED_TUTORIALS_AVAILABLE = False

# Advanced Security Features (v3.0)
from .vulnerability_scanner import VulnerabilityScanner, Vulnerability, VulnerabilitySeverity, VulnerabilityCategory
from .compliance_reporter import ComplianceReporter, ComplianceStandard, ComplianceRequirement
from .threat_modeler import ThreatModeler, ThreatCategory, Threat, AttackComplexity
from .attack_simulator import AttackSimulator, AttackType, AttackResult

# Operational Features (v3.0)
from .cost_estimator import CostEstimator, DeploymentScale, CostBreakdown
from .benchmark_runner import BenchmarkRunner, BenchmarkResult

__all__ = [
    # Core features (v2.0)
    'SchemeComparator',
    'ComparisonMetrics',
    'SecurityAssessor',
    'ThreatLevel',
    'ComponentRecommender',
    'PerformanceLevel',
    'UseCaseCategory',
    'PerformanceEstimator',
    'Platform',
    'SchemeExporter',
    'TutorialManager',
    'Tutorial',

    # Advanced security features (v3.0)
    'VulnerabilityScanner',
    'Vulnerability',
    'VulnerabilitySeverity',
    'VulnerabilityCategory',
    'ComplianceReporter',
    'ComplianceStandard',
    'ComplianceRequirement',
    'ThreatModeler',
    'ThreatCategory',
    'Threat',
    'AttackComplexity',
    'AttackSimulator',
    'AttackType',
    'AttackResult',

    # Operational features (v3.0)
    'CostEstimator',
    'DeploymentScale',
    'CostBreakdown',
    'BenchmarkRunner',
    'BenchmarkResult',
]

# Conditionally add enhanced tutorials
if ENHANCED_TUTORIALS_AVAILABLE:
    __all__.extend(['EnhancedTutorialManager', 'TutorialStep'])

# Feature version
__version__ = '3.0.0'

# Feature count
TOTAL_FEATURES = 13
