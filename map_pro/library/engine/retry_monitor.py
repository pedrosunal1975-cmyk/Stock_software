# Path: library/engine/retry_monitor.py
"""
Retry Monitor

Monitors downloader results and implements intelligent retry logic.
Separate from coordinator for cleaner code organization.

Responsibilities:
- Monitor download results
- Handle retry escalation
- Switch to alternative URLs
- Alert user about failures
"""

from typing import Dict, Any, List
from datetime import datetime

from library.core.logger import get_logger
from library.core.data_paths import LibraryPaths
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class RetryMonitor:
    """
    Monitors download results and implements intelligent retry.
    
    Works with DownloadTracker, URLResolver, and DatabaseConnector.
    """
    
    def __init__(self, download_tracker, url_resolver, db_connector, paths: LibraryPaths):
        """
        Initialize retry monitor.
        
        Args:
            download_tracker: DownloadTracker instance
            url_resolver: URLResolver instance
            db_connector: DatabaseConnector instance
            paths: DataPaths instance
        """
        self.tracker = download_tracker
        self.resolver = url_resolver
        self.db = db_connector
        self.paths = paths
        
        logger.info(f"{LOG_INPUT} RetryMonitor initialized")
    
    def monitor_download_results(self) -> Dict[str, Any]:
        """
        Monitor downloader results and implement retry logic.
        
        Call this periodically (e.g., every minute in --monitor mode)
        to check download status and handle failures.
        
        Returns:
            Summary of actions taken
        """
        logger.info(f"{LOG_PROCESS} Monitoring download results")
        
        # Get libraries needing retry
        pending_retries = self.tracker.get_pending_retries()
        
        # Get permanently failed libraries
        failed = self.tracker.get_failed_downloads()
        
        logger.info(
            f"{LOG_OUTPUT} Found {len(pending_retries)} pending retries, "
            f"{len(failed)} permanent failures"
        )
        
        # Process retries
        retry_actions = []
        for lib in pending_retries:
            action = self._handle_retry(lib)
            retry_actions.append(action)
        
        # Alert user about permanent failures
        for lib in failed:
            self._alert_user_persistent_failure(lib)
        
        return {
            'pending_retries': len(pending_retries),
            'permanent_failures': len(failed),
            'retry_actions': retry_actions,
        }
    
    def _handle_retry(self, library: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle retry for a failed download.
        
        Implements intelligent escalation:
        1. Attempts 1-3: Retry same URL
        2. Attempts 4-6: Try alternative URLs
        3. After 6: Alert user, mark failed
        
        Args:
            library: Library info with failure reason
            
        Returns:
            Action taken
        """
        taxonomy_name = library['taxonomy_name']
        version = library['version']
        retry_strategy = library['retry_strategy']
        
        logger.info(
            f"{LOG_PROCESS} Handling retry for {taxonomy_name} v{version}: "
            f"strategy={retry_strategy}"
        )
        
        if retry_strategy == 'retry_same_url':
            # Just retry - downloader will pick it up
            # Reset status to pending
            self.db.save_taxonomy({
                'taxonomy_name': taxonomy_name,
                'version': version,
                'status': 'pending',  # Signal downloader to retry
            })
            
            logger.info(f"{LOG_OUTPUT} Queued {taxonomy_name} v{version} for retry (same URL)")
            
            return {
                'taxonomy': f"{taxonomy_name} v{version}",
                'action': 'retry_same_url',
            }
        
        elif retry_strategy == 'try_alternative_url':
            # Get alternative URL
            status = self.tracker.get_download_status(taxonomy_name, version)
            namespace = status.get('namespace', '')
            
            alt_url = self.resolver.get_alternative_url(
                taxonomy_name,
                version,
                namespace
            )
            
            if alt_url:
                # Switch to alternative URL
                self.tracker.try_alternative_url(taxonomy_name, version, alt_url)
                
                # Queue for retry
                self.db.save_taxonomy({
                    'taxonomy_name': taxonomy_name,
                    'version': version,
                    'status': 'pending',
                })
                
                logger.info(
                    f"{LOG_OUTPUT} Switched {taxonomy_name} v{version} "
                    f"to alternative URL: {alt_url}"
                )
                
                return {
                    'taxonomy': f"{taxonomy_name} v{version}",
                    'action': 'try_alternative_url',
                    'url': alt_url,
                }
            else:
                logger.warning(
                    f"No alternative URL available for {taxonomy_name} v{version}"
                )
                
                # Mark as failed, alert user
                self.tracker.record_download_failure(
                    taxonomy_name,
                    version,
                    'download',
                    'no_alternative_url',
                    'All URLs exhausted, no alternatives available'
                )
                
                self._alert_user_manual_download_needed(
                    taxonomy_name,
                    version,
                    status
                )
                
                return {
                    'taxonomy': f"{taxonomy_name} v{version}",
                    'action': 'alert_user_no_alternatives',
                }
        
        elif retry_strategy == 'manual_intervention':
            # Need user to fix system issue
            status = self.tracker.get_download_status(taxonomy_name, version)
            
            self._alert_user_manual_intervention(
                taxonomy_name,
                version,
                status
            )
            
            return {
                'taxonomy': f"{taxonomy_name} v{version}",
                'action': 'alert_user_manual_intervention',
            }
        
        else:
            # Unknown strategy
            logger.warning(f"Unknown retry strategy: {retry_strategy}")
            return {
                'taxonomy': f"{taxonomy_name} v{version}",
                'action': 'unknown_strategy',
            }
    
    def _alert_user_persistent_failure(self, library: Dict[str, Any]) -> None:
        """
        Alert user about library that failed after all retry attempts.
        
        Args:
            library: Failed library info
        """
        taxonomy_name = library['taxonomy_name']
        version = library['version']
        
        logger.error(
            f"PERSISTENT FAILURE: {taxonomy_name} v{version} "
            f"failed after {library['total_attempts']} attempts"
        )
        
        # Get full status
        status = self.tracker.get_download_status(taxonomy_name, version)
        
        # Generate detailed report
        report = f"""
{'=' * 80}
PERSISTENT DOWNLOAD FAILURE - MANUAL DOWNLOAD REQUIRED
{'=' * 80}

Library: {taxonomy_name} v{version}
Attempts: {library['total_attempts']}
Last failure: {library.get('failure_stage')} - {library.get('failure_reason')}

URLs Tried:
{chr(10).join('  • ' + url for url in library.get('urls_tried', []))}

Manual Download Instructions:
1. Search online for: "{taxonomy_name} {version} taxonomy download"
2. Download the ZIP file from official source
3. Place in: {self.paths.manual_downloads}
4. Run: python library.py --process-manual {taxonomy_name}-{version}.zip

{'=' * 80}
"""
        
        # Log to console
        print(report)
        
        # Log to file
        logger.error(report)
    
    def _alert_user_manual_download_needed(
        self,
        taxonomy_name: str,
        version: str,
        status: Dict[str, Any]
    ) -> None:
        """
        Alert user that automatic download exhausted, manual needed.
        
        Args:
            taxonomy_name: Taxonomy name
            version: Version
            status: Download status from database
        """
        logger.warning(
            f"MANUAL DOWNLOAD NEEDED: {taxonomy_name} v{version} "
            f"- all automatic attempts exhausted"
        )
        
        report = f"""
{'=' * 80}
MANUAL DOWNLOAD NEEDED
{'=' * 80}

Library: {taxonomy_name} v{version}
Reason: All automatic download URLs failed

Namespace: {status.get('namespace', 'unknown')}

URLs attempted:
  • Primary: {status.get('current_url')}
{chr(10).join('  • ' + url for url in status.get('urls_tried', []))}

Please download manually:
1. Visit official source for {taxonomy_name}
2. Download version {version}
3. Place ZIP in: {self.paths.manual_downloads}
4. Run: python library.py --process-manual <filename>.zip

{'=' * 80}
"""
        
        print(report)
        logger.warning(report)
    
    def _alert_user_manual_intervention(
        self,
        taxonomy_name: str,
        version: str,
        status: Dict[str, Any]
    ) -> None:
        """
        Alert user that manual intervention needed (system issue).
        
        Args:
            taxonomy_name: Taxonomy name
            version: Version
            status: Download status from database
        """
        failure_reason = status.get('failure_reason', 'unknown')
        
        logger.error(
            f"MANUAL INTERVENTION: {taxonomy_name} v{version} "
            f"- system issue: {failure_reason}"
        )
        
        # Provide specific instructions based on failure reason
        if failure_reason == 'permission_denied':
            instructions = """
Check file permissions:
- Ensure library module has write access to taxonomy directories
- Run: chmod -R u+w /mnt/map_pro/taxonomies/
"""
        elif failure_reason == 'disk_full':
            instructions = """
Free up disk space:
- Check available space: df -h /mnt/map_pro
- Remove old files or expand storage
"""
        else:
            instructions = f"""
System error encountered: {failure_reason}
Check logs for details: {self.paths.log_dir}
"""
        
        report = f"""
{'=' * 80}
MANUAL INTERVENTION REQUIRED
{'=' * 80}

Library: {taxonomy_name} v{version}
Issue: {failure_reason}

{instructions}

After fixing, retry with:
python library.py --scan

{'=' * 80}
"""
        
        print(report)
        logger.error(report)
    
    def get_download_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive download status summary.
        
        Returns:
            Summary statistics
        """
        from database.models import session_scope, TaxonomyLibrary
        
        with session_scope() as session:
            total = session.query(TaxonomyLibrary).count()
            
            ready = session.query(TaxonomyLibrary).filter(
                TaxonomyLibrary.download_status == 'ready'
            ).count()
            
            pending = session.query(TaxonomyLibrary).filter(
                TaxonomyLibrary.status == 'pending'
            ).count()
            
            downloading = session.query(TaxonomyLibrary).filter(
                TaxonomyLibrary.download_status.in_(['downloading', 'extracting'])
            ).count()
            
            failed_retry = session.query(TaxonomyLibrary).filter(
                TaxonomyLibrary.download_status == 'failed',
                TaxonomyLibrary.total_attempts < 6
            ).count()
            
            failed_permanent = session.query(TaxonomyLibrary).filter(
                TaxonomyLibrary.status == 'failed'
            ).count()
            
            return {
                'total_libraries': total,
                'ready': ready,
                'pending_download': pending,
                'currently_downloading': downloading,
                'failed_will_retry': failed_retry,
                'failed_permanent': failed_permanent,
                'success_rate': (ready / total * 100) if total > 0 else 0,
            }


__all__ = ['RetryMonitor']