"""
Cost Estimator
估算密码学实现的各项成本

Provides comprehensive cost estimation for cryptographic implementations including
development, testing, deployment, licensing, maintenance, hardware, and training costs.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import math


class DeploymentScale(Enum):
    """Deployment scale categories"""
    SMALL = "small"  # <1K users
    MEDIUM = "medium"  # 1K-100K users
    LARGE = "large"  # 100K-1M users
    ENTERPRISE = "enterprise"  # >1M users


class ComplexityLevel(Enum):
    """Implementation complexity levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


@dataclass
class CostBreakdown:
    """Detailed cost breakdown"""
    development: float
    testing: float
    deployment: float
    licensing: float
    maintenance_yearly: float
    hardware: float
    training: float
    total_upfront: float
    total_yearly: float

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class TimelinePhase:
    """Development timeline phase"""
    name: str
    duration_weeks: int
    cost: float
    dependencies: List[str]
    deliverables: List[str]


@dataclass
class ROIAnalysis:
    """Return on investment analysis"""
    total_investment: float
    yearly_savings: float
    break_even_months: float
    five_year_roi: float
    risk_reduction_value: float
    compliance_value: float


class CostEstimator:
    """Estimate implementation costs for cryptographic schemes"""

    # Base hourly rates (USD)
    SENIOR_DEVELOPER_RATE = 150
    DEVELOPER_RATE = 100
    SECURITY_EXPERT_RATE = 200
    QA_ENGINEER_RATE = 80
    DEVOPS_RATE = 120

    # Complexity multipliers for different algorithms
    ALGORITHM_COMPLEXITY = {
        'AES': ComplexityLevel.LOW,
        'ChaCha20': ComplexityLevel.LOW,
        'RSA': ComplexityLevel.MEDIUM,
        'ECDSA': ComplexityLevel.MEDIUM,
        'Ed25519': ComplexityLevel.MEDIUM,
        'Kyber': ComplexityLevel.HIGH,
        'Dilithium': ComplexityLevel.HIGH,
        'SPHINCS+': ComplexityLevel.VERY_HIGH,
        'FrodoKEM': ComplexityLevel.HIGH,
        'Custom': ComplexityLevel.VERY_HIGH,
    }

    # Hardware costs by scale (USD)
    HARDWARE_COSTS = {
        DeploymentScale.SMALL: {
            'servers': 5000,
            'hsm': 0,  # Optional for small scale
            'crypto_accelerator': 0,
            'backup': 2000,
        },
        DeploymentScale.MEDIUM: {
            'servers': 25000,
            'hsm': 15000,
            'crypto_accelerator': 5000,
            'backup': 10000,
        },
        DeploymentScale.LARGE: {
            'servers': 100000,
            'hsm': 50000,
            'crypto_accelerator': 20000,
            'backup': 40000,
        },
        DeploymentScale.ENTERPRISE: {
            'servers': 500000,
            'hsm': 200000,
            'crypto_accelerator': 100000,
            'backup': 200000,
        },
    }

    # Licensing costs (yearly, USD)
    LICENSE_COSTS = {
        'RSA': 0,  # Public domain
        'AES': 0,
        'ECDSA': 0,
        'ChaCha20': 0,
        'Ed25519': 0,
        'Kyber': 0,  # NIST standard, no licensing
        'Dilithium': 0,
        'SPHINCS+': 0,
        'Commercial_Library': {
            DeploymentScale.SMALL: 5000,
            DeploymentScale.MEDIUM: 25000,
            DeploymentScale.LARGE: 100000,
            DeploymentScale.ENTERPRISE: 500000,
        }
    }

    def __init__(self):
        """Initialize cost estimator"""
        self.base_development_hours = 160  # 1 month baseline

    def estimate_costs(self,
                      scheme: Dict[str, Any],
                      scale: DeploymentScale,
                      timeline_months: int = 6,
                      use_commercial_library: bool = False) -> Dict[str, Any]:
        """
        Comprehensive cost estimation

        Args:
            scheme: Cryptographic scheme details
            scale: Deployment scale
            timeline_months: Development timeline in months
            use_commercial_library: Whether to use commercial crypto library

        Returns:
            Dictionary containing:
            - cost_breakdown: Detailed costs
            - timeline: Development phases
            - roi_analysis: Return on investment
            - alternatives: Cost comparison with alternatives
            - recommendations: Cost optimization recommendations
        """
        # Determine complexity
        algorithm = scheme.get('algorithm', 'Custom')
        complexity = self.ALGORITHM_COMPLEXITY.get(algorithm, ComplexityLevel.HIGH)

        # Calculate individual costs
        dev_cost = self.estimate_development_cost(scheme, timeline_months, complexity)
        testing_cost = self.estimate_testing_cost(scheme, complexity, scale)
        deployment_cost = self.estimate_deployment_cost(scale)
        licensing_cost = self.estimate_licensing_cost(
            scheme, scale, use_commercial_library
        )
        maintenance_cost = self.estimate_maintenance_cost(dev_cost, scale)
        hardware_cost = self.estimate_hardware_cost(scheme, scale)
        training_cost = self.estimate_training_cost(scale, complexity)

        # Calculate totals
        total_upfront = (dev_cost + testing_cost + deployment_cost +
                        hardware_cost + training_cost)
        total_yearly = maintenance_cost + licensing_cost

        cost_breakdown = CostBreakdown(
            development=dev_cost,
            testing=testing_cost,
            deployment=deployment_cost,
            licensing=licensing_cost,
            maintenance_yearly=maintenance_cost,
            hardware=hardware_cost,
            training=training_cost,
            total_upfront=total_upfront,
            total_yearly=total_yearly
        )

        # Generate timeline
        timeline = self._generate_timeline(scheme, timeline_months, complexity)

        # Calculate ROI
        breach_risk_reduction = scheme.get('security_level', 128) / 256.0
        roi_analysis = self.calculate_roi(
            cost_breakdown,
            breach_risk_reduction,
            scale
        )

        # Generate alternatives
        alternatives = self._generate_alternatives(scheme, scale, timeline_months)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            cost_breakdown,
            complexity,
            scale,
            use_commercial_library
        )

        return {
            'cost_breakdown': cost_breakdown.to_dict(),
            'timeline': timeline,
            'roi_analysis': asdict(roi_analysis),
            'alternatives': alternatives,
            'recommendations': recommendations,
            'metadata': {
                'algorithm': algorithm,
                'complexity': complexity.name,
                'scale': scale.value,
                'timeline_months': timeline_months,
                'use_commercial_library': use_commercial_library,
            }
        }

    def estimate_development_cost(self,
                                  scheme: Dict,
                                  timeline_months: int,
                                  complexity: ComplexityLevel) -> float:
        """
        Estimate development costs

        Based on:
        - Algorithm complexity
        - Team size and composition
        - Development timeline
        - Required security level
        """
        # Base hours adjusted by complexity
        complexity_multiplier = {
            ComplexityLevel.LOW: 1.0,
            ComplexityLevel.MEDIUM: 2.0,
            ComplexityLevel.HIGH: 3.5,
            ComplexityLevel.VERY_HIGH: 5.0,
        }

        base_hours = self.base_development_hours * complexity_multiplier[complexity]

        # Adjust for security requirements
        security_level = scheme.get('security_level', 128)
        if security_level >= 256:
            base_hours *= 1.5
        elif security_level >= 192:
            base_hours *= 1.3

        # Adjust for quantum resistance
        if scheme.get('quantum_resistant', False):
            base_hours *= 1.8

        # Team composition (percentage of time)
        senior_dev_hours = base_hours * 0.3
        dev_hours = base_hours * 0.4
        security_expert_hours = base_hours * 0.2
        devops_hours = base_hours * 0.1

        # Calculate costs
        total_cost = (
            senior_dev_hours * self.SENIOR_DEVELOPER_RATE +
            dev_hours * self.DEVELOPER_RATE +
            security_expert_hours * self.SECURITY_EXPERT_RATE +
            devops_hours * self.DEVOPS_RATE
        )

        # Adjust for timeline (rushed timeline = overtime premium)
        if timeline_months < 4:
            total_cost *= 1.3  # 30% rush premium
        elif timeline_months > 12:
            total_cost *= 0.9  # 10% discount for extended timeline

        return round(total_cost, 2)

    def estimate_testing_cost(self,
                             scheme: Dict,
                             complexity: ComplexityLevel,
                             scale: DeploymentScale) -> float:
        """
        Estimate testing and security audit costs

        Includes:
        - Unit testing
        - Integration testing
        - Security audits
        - Penetration testing
        - Compliance testing
        """
        # Base testing is 30-50% of development time
        complexity_testing_factor = {
            ComplexityLevel.LOW: 0.3,
            ComplexityLevel.MEDIUM: 0.4,
            ComplexityLevel.HIGH: 0.5,
            ComplexityLevel.VERY_HIGH: 0.6,
        }

        # Estimate QA hours
        dev_hours = self.base_development_hours
        testing_hours = dev_hours * complexity_testing_factor[complexity]

        qa_cost = testing_hours * self.QA_ENGINEER_RATE

        # Security audit costs (external)
        audit_costs = {
            DeploymentScale.SMALL: 15000,
            DeploymentScale.MEDIUM: 40000,
            DeploymentScale.LARGE: 100000,
            DeploymentScale.ENTERPRISE: 250000,
        }

        security_audit_cost = audit_costs[scale]

        # Penetration testing
        pentest_costs = {
            DeploymentScale.SMALL: 10000,
            DeploymentScale.MEDIUM: 25000,
            DeploymentScale.LARGE: 60000,
            DeploymentScale.ENTERPRISE: 150000,
        }

        pentest_cost = pentest_costs[scale]

        # Compliance testing (if required)
        compliance_cost = 0
        if scheme.get('compliance_required', False):
            compliance_costs = {
                DeploymentScale.SMALL: 5000,
                DeploymentScale.MEDIUM: 15000,
                DeploymentScale.LARGE: 40000,
                DeploymentScale.ENTERPRISE: 100000,
            }
            compliance_cost = compliance_costs[scale]

        total = qa_cost + security_audit_cost + pentest_cost + compliance_cost
        return round(total, 2)

    def estimate_deployment_cost(self, scale: DeploymentScale) -> float:
        """
        Estimate deployment costs

        Includes:
        - Infrastructure setup
        - CI/CD pipeline
        - Monitoring setup
        - Documentation
        """
        base_costs = {
            DeploymentScale.SMALL: 8000,
            DeploymentScale.MEDIUM: 25000,
            DeploymentScale.LARGE: 75000,
            DeploymentScale.ENTERPRISE: 200000,
        }

        return base_costs[scale]

    def estimate_licensing_cost(self,
                               scheme: Dict,
                               scale: DeploymentScale,
                               use_commercial_library: bool) -> float:
        """
        Estimate licensing costs (yearly)

        Includes:
        - Algorithm patents (if any)
        - Commercial library licenses
        - HSM licenses
        """
        total_cost = 0.0

        # Algorithm licensing
        algorithm = scheme.get('algorithm', 'Custom')
        if algorithm in self.LICENSE_COSTS:
            algo_cost = self.LICENSE_COSTS[algorithm]
            if isinstance(algo_cost, dict):
                total_cost += algo_cost.get(scale, 0)
            else:
                total_cost += algo_cost

        # Commercial library licensing
        if use_commercial_library:
            lib_costs = self.LICENSE_COSTS['Commercial_Library']
            total_cost += lib_costs[scale]

        # HSM licensing (for medium+ deployments)
        if scale in [DeploymentScale.MEDIUM, DeploymentScale.LARGE,
                    DeploymentScale.ENTERPRISE]:
            hsm_license_costs = {
                DeploymentScale.MEDIUM: 5000,
                DeploymentScale.LARGE: 20000,
                DeploymentScale.ENTERPRISE: 80000,
            }
            total_cost += hsm_license_costs[scale]

        return round(total_cost, 2)

    def estimate_hardware_cost(self,
                              scheme: Dict,
                              scale: DeploymentScale) -> float:
        """
        Estimate hardware costs

        Includes:
        - Servers
        - HSM (Hardware Security Modules)
        - Crypto accelerators
        - Backup infrastructure
        """
        costs = self.HARDWARE_COSTS[scale]

        total = sum(costs.values())

        # Additional costs for quantum-resistant algorithms
        if scheme.get('quantum_resistant', False):
            # May need more powerful hardware
            total *= 1.2

        # High-performance requirements
        if scheme.get('high_performance', False):
            total *= 1.3

        return round(total, 2)

    def estimate_maintenance_cost(self,
                                  development_cost: float,
                                  scale: DeploymentScale) -> float:
        """
        Estimate yearly maintenance costs

        Typically 15-25% of development cost annually
        """
        # Base maintenance percentage
        base_percentage = 0.20

        # Scale affects maintenance
        scale_multipliers = {
            DeploymentScale.SMALL: 0.8,
            DeploymentScale.MEDIUM: 1.0,
            DeploymentScale.LARGE: 1.2,
            DeploymentScale.ENTERPRISE: 1.5,
        }

        maintenance = (development_cost * base_percentage *
                      scale_multipliers[scale])

        return round(maintenance, 2)

    def estimate_training_cost(self,
                              scale: DeploymentScale,
                              complexity: ComplexityLevel) -> float:
        """
        Estimate training costs for development and operations teams
        """
        # Base training costs
        base_costs = {
            DeploymentScale.SMALL: 5000,
            DeploymentScale.MEDIUM: 15000,
            DeploymentScale.LARGE: 40000,
            DeploymentScale.ENTERPRISE: 100000,
        }

        complexity_multipliers = {
            ComplexityLevel.LOW: 0.8,
            ComplexityLevel.MEDIUM: 1.0,
            ComplexityLevel.HIGH: 1.3,
            ComplexityLevel.VERY_HIGH: 1.6,
        }

        cost = base_costs[scale] * complexity_multipliers[complexity]
        return round(cost, 2)

    def calculate_roi(self,
                     costs: CostBreakdown,
                     breach_risk_reduction: float,
                     scale: DeploymentScale) -> ROIAnalysis:
        """
        Calculate ROI based on risk reduction and compliance value

        Args:
            costs: Cost breakdown
            breach_risk_reduction: Risk reduction factor (0-1)
            scale: Deployment scale
        """
        # Estimate average breach costs by scale
        average_breach_costs = {
            DeploymentScale.SMALL: 200000,
            DeploymentScale.MEDIUM: 2000000,
            DeploymentScale.LARGE: 10000000,
            DeploymentScale.ENTERPRISE: 50000000,
        }

        breach_cost = average_breach_costs[scale]

        # Annual breach probability (industry average ~3%)
        annual_breach_probability = 0.03

        # Expected annual loss without crypto improvement
        expected_annual_loss = breach_cost * annual_breach_probability

        # Risk reduction value (yearly savings)
        risk_reduction_value = expected_annual_loss * breach_risk_reduction

        # Compliance value (avoiding fines, maintaining certifications)
        compliance_values = {
            DeploymentScale.SMALL: 50000,
            DeploymentScale.MEDIUM: 200000,
            DeploymentScale.LARGE: 1000000,
            DeploymentScale.ENTERPRISE: 5000000,
        }

        compliance_value = compliance_values[scale] * 0.5  # 50% of potential fine

        # Total yearly savings
        yearly_savings = risk_reduction_value + compliance_value

        # Total investment
        total_investment = costs.total_upfront

        # Break-even calculation
        net_yearly_benefit = yearly_savings - costs.total_yearly

        if net_yearly_benefit > 0:
            break_even_months = (total_investment / net_yearly_benefit) * 12
        else:
            break_even_months = float('inf')

        # 5-year ROI
        five_year_savings = yearly_savings * 5
        five_year_costs = total_investment + (costs.total_yearly * 5)
        five_year_roi = ((five_year_savings - five_year_costs) /
                        five_year_costs * 100)

        return ROIAnalysis(
            total_investment=round(total_investment, 2),
            yearly_savings=round(yearly_savings, 2),
            break_even_months=round(break_even_months, 1),
            five_year_roi=round(five_year_roi, 2),
            risk_reduction_value=round(risk_reduction_value, 2),
            compliance_value=round(compliance_value, 2)
        )

    def _generate_timeline(self,
                          scheme: Dict,
                          timeline_months: int,
                          complexity: ComplexityLevel) -> List[Dict[str, Any]]:
        """Generate development timeline phases"""
        phases = []

        # Phase distribution based on complexity
        if complexity == ComplexityLevel.LOW:
            phase_distribution = {
                'Planning & Design': 0.15,
                'Core Implementation': 0.35,
                'Testing & Security Audit': 0.25,
                'Deployment & Integration': 0.15,
                'Training & Documentation': 0.10,
            }
        elif complexity == ComplexityLevel.MEDIUM:
            phase_distribution = {
                'Planning & Design': 0.20,
                'Core Implementation': 0.30,
                'Testing & Security Audit': 0.25,
                'Deployment & Integration': 0.15,
                'Training & Documentation': 0.10,
            }
        else:  # HIGH or VERY_HIGH
            phase_distribution = {
                'Research & Analysis': 0.15,
                'Planning & Design': 0.20,
                'Core Implementation': 0.25,
                'Testing & Security Audit': 0.25,
                'Deployment & Integration': 0.10,
                'Training & Documentation': 0.05,
            }

        total_weeks = timeline_months * 4.33  # Average weeks per month

        current_dependencies = []
        for phase_name, percentage in phase_distribution.items():
            duration_weeks = int(total_weeks * percentage)

            phase = TimelinePhase(
                name=phase_name,
                duration_weeks=max(1, duration_weeks),
                cost=0,  # Could calculate per-phase costs
                dependencies=current_dependencies.copy(),
                deliverables=self._get_phase_deliverables(phase_name)
            )

            phases.append(asdict(phase))
            current_dependencies = [phase_name]

        return phases

    def _get_phase_deliverables(self, phase_name: str) -> List[str]:
        """Get deliverables for each phase"""
        deliverables_map = {
            'Research & Analysis': [
                'Algorithm selection report',
                'Feasibility study',
                'Risk assessment',
            ],
            'Planning & Design': [
                'Architecture document',
                'API specifications',
                'Security requirements',
                'Test plan',
            ],
            'Core Implementation': [
                'Core crypto library',
                'API implementation',
                'Unit tests',
                'Code documentation',
            ],
            'Testing & Security Audit': [
                'Test results',
                'Security audit report',
                'Penetration test results',
                'Bug fixes',
            ],
            'Deployment & Integration': [
                'Deployment scripts',
                'CI/CD pipeline',
                'Monitoring setup',
                'Production deployment',
            ],
            'Training & Documentation': [
                'User documentation',
                'Developer guides',
                'Training materials',
                'Operations runbook',
            ],
        }

        return deliverables_map.get(phase_name, [])

    def _generate_alternatives(self,
                              scheme: Dict,
                              scale: DeploymentScale,
                              timeline_months: int) -> List[Dict[str, Any]]:
        """Generate cost comparison with alternatives"""
        alternatives = []

        # Alternative 1: Use open-source library
        opensource_costs = self.estimate_costs(
            scheme, scale, timeline_months, use_commercial_library=False
        )

        alternatives.append({
            'name': 'Open-Source Implementation',
            'description': 'Use open-source crypto libraries (OpenSSL, libsodium, etc.)',
            'total_upfront': opensource_costs['cost_breakdown']['total_upfront'],
            'total_yearly': opensource_costs['cost_breakdown']['total_yearly'],
            'pros': [
                'Lower licensing costs',
                'Community support',
                'Transparent code',
            ],
            'cons': [
                'May require more development time',
                'Limited vendor support',
                'Compliance responsibility on team',
            ],
        })

        # Alternative 2: Commercial solution
        commercial_costs = self.estimate_costs(
            scheme, scale, timeline_months, use_commercial_library=True
        )

        alternatives.append({
            'name': 'Commercial Solution',
            'description': 'Use commercial crypto library with vendor support',
            'total_upfront': commercial_costs['cost_breakdown']['total_upfront'],
            'total_yearly': commercial_costs['cost_breakdown']['total_yearly'],
            'pros': [
                'Vendor support and SLA',
                'Faster implementation',
                'Compliance certifications',
            ],
            'cons': [
                'Higher licensing costs',
                'Vendor lock-in',
                'Less flexibility',
            ],
        })

        # Alternative 3: Cloud-managed service
        cloud_managed_cost = self._estimate_cloud_managed_cost(scale)

        alternatives.append({
            'name': 'Cloud-Managed Service',
            'description': 'Use AWS KMS, Azure Key Vault, or Google Cloud KMS',
            'total_upfront': cloud_managed_cost['upfront'],
            'total_yearly': cloud_managed_cost['yearly'],
            'pros': [
                'Minimal upfront cost',
                'Managed infrastructure',
                'Automatic updates and compliance',
            ],
            'cons': [
                'Ongoing operational costs',
                'Cloud vendor dependency',
                'Data residency concerns',
            ],
        })

        return alternatives

    def _estimate_cloud_managed_cost(self, scale: DeploymentScale) -> Dict[str, float]:
        """Estimate costs for cloud-managed crypto services"""
        # Minimal upfront (mainly integration work)
        upfront_costs = {
            DeploymentScale.SMALL: 5000,
            DeploymentScale.MEDIUM: 15000,
            DeploymentScale.LARGE: 40000,
            DeploymentScale.ENTERPRISE: 100000,
        }

        # Yearly operational costs
        yearly_costs = {
            DeploymentScale.SMALL: 3000,
            DeploymentScale.MEDIUM: 20000,
            DeploymentScale.LARGE: 100000,
            DeploymentScale.ENTERPRISE: 500000,
        }

        return {
            'upfront': upfront_costs[scale],
            'yearly': yearly_costs[scale],
        }

    def _generate_recommendations(self,
                                 costs: CostBreakdown,
                                 complexity: ComplexityLevel,
                                 scale: DeploymentScale,
                                 use_commercial_library: bool) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []

        # High development cost
        if costs.development > 200000:
            recommendations.append(
                'Consider using a commercial library to reduce development time and cost'
            )
            recommendations.append(
                'Evaluate if a phased implementation could spread costs over time'
            )

        # High hardware cost
        if costs.hardware > 100000:
            recommendations.append(
                'Consider cloud-based HSM solutions to reduce upfront hardware costs'
            )
            recommendations.append(
                'Evaluate crypto accelerator necessity - software may be sufficient'
            )

        # Complexity optimization
        if complexity in [ComplexityLevel.HIGH, ComplexityLevel.VERY_HIGH]:
            recommendations.append(
                'High complexity detected - ensure team has necessary expertise or budget for consultants'
            )
            recommendations.append(
                'Consider starting with a simpler algorithm and upgrading later if needed'
            )

        # Scale optimization
        if scale == DeploymentScale.SMALL and costs.total_upfront > 100000:
            recommendations.append(
                'For small scale, consider SaaS crypto solutions to minimize upfront investment'
            )

        # Testing costs
        if costs.testing > costs.development * 0.5:
            recommendations.append(
                'Testing costs are high - ensure adequate test automation to reduce long-term costs'
            )

        # Licensing costs
        if costs.licensing > 50000:
            recommendations.append(
                'Evaluate open-source alternatives to reduce licensing costs'
            )

        # General recommendations
        if not use_commercial_library and complexity == ComplexityLevel.LOW:
            recommendations.append(
                'Open-source libraries are mature for this algorithm - good choice for cost savings'
            )

        recommendations.append(
            'Implement comprehensive monitoring to detect issues early and reduce maintenance costs'
        )

        recommendations.append(
            'Invest in thorough documentation to reduce long-term training and onboarding costs'
        )

        return recommendations


# Example usage
if __name__ == '__main__':
    estimator = CostEstimator()

    # Example: Estimate costs for AES-256 implementation
    aes_scheme = {
        'algorithm': 'AES',
        'security_level': 256,
        'quantum_resistant': False,
        'compliance_required': True,
        'high_performance': True,
    }

    result = estimator.estimate_costs(
        scheme=aes_scheme,
        scale=DeploymentScale.MEDIUM,
        timeline_months=6,
        use_commercial_library=False
    )

    print("Cost Estimation for AES-256 Implementation")
    print("=" * 50)
    print(f"\nCost Breakdown:")
    for key, value in result['cost_breakdown'].items():
        print(f"  {key}: ${value:,.2f}")

    print(f"\nROI Analysis:")
    for key, value in result['roi_analysis'].items():
        if 'months' in key:
            print(f"  {key}: {value:.1f} months")
        elif 'roi' in key:
            print(f"  {key}: {value:.2f}%")
        else:
            print(f"  {key}: ${value:,.2f}")

    print(f"\nRecommendations:")
    for i, rec in enumerate(result['recommendations'], 1):
        print(f"  {i}. {rec}")
