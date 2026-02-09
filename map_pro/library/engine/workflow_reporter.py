# Path: library/engine/workflow_reporter.py
"""
Workflow Reporter

Generates user-facing reports and recommendations.
No hardcoded logic - formats results from other components.

Usage:
    from library.engine.workflow_reporter import WorkflowReporter
    
    reporter = WorkflowReporter()
    
    report = reporter.generate_filing_report(
        filing_id='sec/Apple_Inc/10-K/123',
        namespaces=[...],
        libraries_required=[...],
        availability_status={...}
    )
    
    print(reporter.format_report(report))
"""

from typing import Dict, Any, List, Set

from library.core.logger import get_logger
from library.constants import LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class WorkflowReporter:
    """
    Generate workflow reports and recommendations.
    
    Creates user-friendly reports with:
    - Summary of processing
    - Library availability status
    - Actionable recommendations
    
    Example:
        reporter = WorkflowReporter()
        
        report = reporter.generate_filing_report(...)
        formatted = reporter.format_report(report)
        print(formatted)
    """
    
    def __init__(self):
        """Initialize workflow reporter."""
        logger.debug(f"{LOG_OUTPUT} Workflow reporter initialized")
    
    def generate_filing_report(
        self,
        filing_id: str,
        namespaces: Set[str],
        libraries_required: List[Dict[str, Any]],
        availability_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive filing report.
        
        Args:
            filing_id: Filing identifier
            namespaces: Set of namespace URIs detected
            libraries_required: List of required library metadata
            availability_status: Availability check results
            
        Returns:
            Dictionary with report data
        """
        available = availability_status['available_count']
        required = len(libraries_required)
        
        completion_pct = self._calculate_completion_percentage(available, required)
        
        recommendations = self._generate_recommendations(availability_status)
        
        return {
            'filing_id': filing_id,
            'namespaces_count': len(namespaces),
            'libraries_required_count': required,
            'libraries_available_count': available,
            'completion_percentage': completion_pct,
            'libraries_ready': availability_status['missing_count'] == 0,
            'recommendations': recommendations,
            'namespaces': list(namespaces),
            'required_libraries': libraries_required,
            'available_libraries': availability_status['available_libraries'],
            'missing_libraries': availability_status['missing_libraries'],
        }
    
    def format_report(self, report: Dict[str, Any]) -> str:
        """
        Format report as human-readable text.
        
        Args:
            report: Report dictionary
            
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"FILING ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"\nFiling: {report['filing_id']}")
        lines.append(f"\nNamespaces Detected: {report['namespaces_count']}")
        
        for ns in report['namespaces']:
            lines.append(f"  - {ns}")
        
        lines.append(f"\nLibraries Required: {report['libraries_required_count']}")
        lines.append(f"Libraries Available: {report['libraries_available_count']}")
        lines.append(f"Completion: {report['completion_percentage']}%")
        
        if report['libraries_ready']:
            lines.append(f"\n✓ All libraries ready")
        else:
            lines.append(f"\n⚠ Missing {len(report['missing_libraries'])} libraries")
        
        if report['recommendations']:
            lines.append(f"\nRecommendations:")
            for rec in report['recommendations']:
                lines.append(f"  • {rec}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    def _calculate_completion_percentage(
        self,
        available: int,
        required: int
    ) -> float:
        """
        Calculate completion percentage safely.
        
        Args:
            available: Number available
            required: Number required
            
        Returns:
            Percentage (0.0 to 100.0)
        """
        if required == 0:
            return 100.0
        
        percentage = (available / max(required, 1)) * 100
        return round(min(max(percentage, 0.0), 100.0), 2)
    
    def _generate_recommendations(
        self,
        availability_status: Dict[str, Any]
    ) -> List[str]:
        """
        Generate actionable recommendations.
        
        Args:
            availability_status: Availability check results
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        missing = availability_status.get('missing_libraries', [])
        
        if not missing:
            recommendations.append("All required libraries are available")
        else:
            recommendations.append(
                f"{len(missing)} libraries need to be downloaded"
            )
            
            # Suggest checking downloader module
            recommendations.append(
                "Run downloader module to process pending libraries"
            )
            
            # List missing libraries
            for lib in missing[:3]:  # Show first 3
                name = lib.get('taxonomy_name', 'unknown')
                version = lib.get('version', 'unknown')
                recommendations.append(
                    f"  - {name} v{version}"
                )
            
            if len(missing) > 3:
                recommendations.append(
                    f"  ... and {len(missing) - 3} more"
                )
        
        return recommendations


__all__ = ['WorkflowReporter']