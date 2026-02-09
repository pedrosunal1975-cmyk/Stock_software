# Path: library/engine/manual_processor.py
"""
Manual Processor

Handles manually downloaded taxonomy files.

Directories:
- manual_downloads/  - User places ZIP files here
- libraries/         - Extracted taxonomies

Architecture:
1. User downloads taxonomy ZIP manually
2. Places in manual_downloads/
3. System processes and extracts (auto-detects taxonomy name/version)
4. Registers in database
5. ZIP files remain in manual_downloads/ for re-processing if needed

100% AGNOSTIC - no hardcoded taxonomy logic.

Usage:
    from library.engine.manual_processor import ManualProcessor

    processor = ManualProcessor()

    # Process all files automatically (auto-detects name/version)
    results = processor.process_all_manual_files()

    # Or process specific file
    result = processor.process_manual_file(
        'us-gaap-2024.zip',
        taxonomy_name='us-gaap',
        version='2024'
    )
"""

import re
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from library.core.config_loader import LibraryConfig
from library.core.data_paths import LibraryPaths
from library.core.logger import get_logger
from library.constants import LOG_INPUT, LOG_PROCESS, LOG_OUTPUT

logger = get_logger(__name__, 'engine')


class ManualProcessor:
    """
    Process manually downloaded taxonomy files.

    Two-directory pattern:
    - manual_downloads/: User drops ZIP files (files remain here)
    - libraries/: Extracted taxonomies

    Example:
        processor = ManualProcessor()
        
        # Scan for new files
        files = processor.scan_manual_directory()
        
        # Process file
        result = processor.process_manual_file(
            'us-gaap-2024.zip',
            'us-gaap',
            '2024'
        )
    """
    
    def __init__(
        self,
        config: Optional[LibraryConfig] = None,
        paths: Optional[LibraryPaths] = None
    ):
        """
        Initialize manual processor.
        
        Args:
            config: Optional LibraryConfig instance
            paths: Optional LibraryPaths instance
        """
        self.config = config if config else LibraryConfig()
        self.paths = paths if paths else LibraryPaths(self.config)
        
        logger.debug(f"{LOG_PROCESS} Manual processor initialized")
    
    def scan_manual_directory(self) -> List[Dict[str, Any]]:
        """
        Scan manual downloads directory for files.

        Returns:
            List of file information dictionaries
        """
        logger.info(f"{LOG_INPUT} Scanning manual downloads directory")

        if not self.paths.manual_downloads.exists():
            logger.warning("Manual downloads directory does not exist")
            return []

        files = []
        for file_path in self.paths.manual_downloads.iterdir():
            if file_path.is_file():
                # Auto-detect taxonomy info from filename
                detected = self.detect_taxonomy_from_filename(file_path.name)

                files.append({
                    'filename': file_path.name,
                    'path': file_path,
                    'size_mb': file_path.stat().st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                    'detected_name': detected[0],
                    'detected_version': detected[1],
                    'auto_detected': detected[0] is not None,
                })

        logger.info(f"{LOG_OUTPUT} Found {len(files)} files in manual downloads")

        return files

    def detect_taxonomy_from_filename(
        self,
        filename: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Auto-detect taxonomy name and version from filename.

        Handles various naming patterns:
        - IFRS-Taxonomy-2022.zip -> (ifrs-full, 2022)
        - IFRSAT-2022-03-24.zip -> (ifrs-full, 2022)
        - full_ifrs-2022.zip -> (ifrs-full, 2022)
        - ifrs-full-2022.zip -> (ifrs-full, 2022)
        - us-gaap-2024.zip -> (us-gaap, 2024)
        - uk-gaap-2023.zip -> (uk-gaap, 2023)

        Args:
            filename: ZIP filename

        Returns:
            Tuple of (taxonomy_name, version) or (None, None) if not detected
        """
        filename_lower = filename.lower()

        # IFRS patterns
        ifrs_patterns = [
            # IFRS-Taxonomy-2022.zip or IFRS-Taxonomy-2022-03-24.zip
            r'ifrs[-_]?taxonomy[-_](\d{4})',
            # IFRSAT-2022-03-24.zip (Annotated Taxonomy)
            r'ifrsat[-_](\d{4})',
            # full_ifrs-2022.zip or full-ifrs-2022.zip
            r'full[-_]ifrs[-_](\d{4})',
            # ifrs-full-2022.zip
            r'ifrs[-_]full[-_](\d{4})',
            # Just ifrs-2022.zip or ifrs_2022.zip
            r'^ifrs[-_](\d{4})',
        ]

        for pattern in ifrs_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                version = match.group(1)
                logger.debug(
                    f"{LOG_PROCESS} Detected IFRS taxonomy: "
                    f"ifrs-full v{version} from {filename}"
                )
                return ('ifrs-full', version)

        # US-GAAP patterns
        usgaap_patterns = [
            r'us[-_]?gaap[-_](\d{4})',
            r'fasb[-_](\d{4})',
        ]

        for pattern in usgaap_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                version = match.group(1)
                logger.debug(
                    f"{LOG_PROCESS} Detected US-GAAP taxonomy: "
                    f"us-gaap v{version} from {filename}"
                )
                return ('us-gaap', version)

        # UK-GAAP patterns
        ukgaap_patterns = [
            r'uk[-_]?gaap[-_](\d{4})',
            r'frc[-_](\d{4})',
        ]

        for pattern in ukgaap_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                version = match.group(1)
                logger.debug(
                    f"{LOG_PROCESS} Detected UK-GAAP taxonomy: "
                    f"uk-gaap v{version} from {filename}"
                )
                return ('uk-gaap', version)

        # Generic pattern: name-version.zip
        generic_match = re.match(r'^([a-z][\w-]+?)[-_](\d{4})\.zip$', filename_lower)
        if generic_match:
            name = generic_match.group(1)
            version = generic_match.group(2)
            logger.debug(
                f"{LOG_PROCESS} Detected generic taxonomy: "
                f"{name} v{version} from {filename}"
            )
            return (name, version)

        logger.warning(
            f"{LOG_PROCESS} Could not auto-detect taxonomy from: {filename}"
        )
        return (None, None)

    def process_all_manual_files(self) -> Dict[str, Any]:
        """
        Process all ZIP files in manual_downloads directory automatically.

        Auto-detects taxonomy name and version from filenames.
        Extracts each to proper nested directory structure.

        Returns:
            Dictionary with processing results
        """
        logger.info(f"{LOG_INPUT} Processing all manual files")

        files = self.scan_manual_directory()

        if not files:
            return {
                'success': True,
                'total': 0,
                'processed': 0,
                'failed': 0,
                'results': [],
                'message': 'No files found in manual_downloads directory',
            }

        # Filter to only ZIP files
        zip_files = [f for f in files if f['filename'].lower().endswith('.zip')]

        if not zip_files:
            return {
                'success': True,
                'total': len(files),
                'processed': 0,
                'failed': 0,
                'results': [],
                'message': f'Found {len(files)} files but none are ZIP archives',
            }

        results = []
        processed = 0
        failed = 0

        for file_info in zip_files:
            filename = file_info['filename']
            taxonomy_name = file_info.get('detected_name')
            version = file_info.get('detected_version')

            if not taxonomy_name or not version:
                results.append({
                    'filename': filename,
                    'success': False,
                    'error': 'Could not auto-detect taxonomy name/version from filename',
                })
                failed += 1
                continue

            # Process this file
            result = self.process_manual_file(
                filename=filename,
                taxonomy_name=taxonomy_name,
                version=version
            )

            result['filename'] = filename
            result['taxonomy_name'] = taxonomy_name
            result['version'] = version
            results.append(result)

            if result['success']:
                processed += 1
            else:
                failed += 1

        logger.info(
            f"{LOG_OUTPUT} Processed {processed}/{len(zip_files)} files, "
            f"{failed} failed"
        )

        return {
            'success': failed == 0,
            'total': len(zip_files),
            'processed': processed,
            'failed': failed,
            'results': results,
        }
    
    def process_manual_file(
        self,
        filename: str,
        taxonomy_name: str,
        version: str,
        namespace: Optional[str] = None,
        authority: Optional[str] = None,
        market_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process manually downloaded taxonomy file.

        Steps:
        1. Extract ZIP to libraries directory
        2. Count files
        3. ZIP file remains in manual_downloads/ for future re-processing

        Args:
            filename: File in manual_downloads directory
            taxonomy_name: Taxonomy name (e.g., 'us-gaap')
            version: Taxonomy version (e.g., '2024')
            namespace: Optional namespace URI
            authority: Optional authority (e.g., 'FASB')
            market_types: Optional list of markets (e.g., ['sec'])

        Returns:
            Dictionary with processing result
        """
        logger.info(f"{LOG_INPUT} Processing manual file: {filename}")

        source_path = self.paths.get_manual_file_path(filename)

        if not source_path.exists():
            return {
                'success': False,
                'error': f'File not found: {filename}',
            }

        try:
            # Extract to libraries directory
            target_dir = self.paths.get_library_directory(taxonomy_name, version)

            logger.debug(f"{LOG_PROCESS} Extracting to {target_dir}")

            extract_result = self._extract_archive(source_path, target_dir)

            if not extract_result['success']:
                return extract_result

            logger.info(f"{LOG_OUTPUT} Successfully processed {filename}")

            return {
                'success': True,
                'extract_path': str(target_dir),
                'file_count': extract_result['file_count'],
            }

        except Exception as e:
            logger.error(f"Error processing manual file {filename}: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def register_manual_library(
        self,
        taxonomy_name: str,
        version: str,
        namespace: str,
        download_url: str,
        authority: str,
        market_types: List[str]
    ) -> Dict[str, Any]:
        """
        Register manually processed library in database.
        
        Delegates to DatabaseConnector → searcher.
        
        Args:
            taxonomy_name: Taxonomy name
            version: Version
            namespace: Namespace URI
            download_url: Download URL (can be manual source)
            authority: Authority
            market_types: List of markets
            
        Returns:
            Dictionary with registration result
        """
        logger.info(
            f"{LOG_INPUT} Registering manual library: "
            f"{taxonomy_name} v{version}"
        )
        
        try:
            from library.engine.db_connector import DatabaseConnector
            
            db = DatabaseConnector(self.config)
            
            metadata = {
                'taxonomy_name': taxonomy_name,
                'version': version,
                'namespace': namespace,
                'download_url': download_url,
                'market_type': ','.join(market_types) if market_types else 'unknown',
                'authority': authority,
            }
            
            result = db.save_taxonomy(metadata)
            
            if result['success']:
                logger.info(f"{LOG_OUTPUT} Registered {taxonomy_name} v{version}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error registering manual library: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def _extract_archive(
        self,
        archive_path: Path,
        target_dir: Path
    ) -> Dict[str, Any]:
        """
        Extract ZIP archive to target directory.
        
        Args:
            archive_path: Path to ZIP file
            target_dir: Target extraction directory
            
        Returns:
            Dictionary with extraction result
        """
        try:
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            # Count extracted files
            file_count = sum(1 for _ in target_dir.rglob('*') if _.is_file())
            
            logger.debug(f"{LOG_OUTPUT} Extracted {file_count} files")
            
            return {
                'success': True,
                'file_count': file_count,
            }
            
        except zipfile.BadZipFile:
            return {
                'success': False,
                'error': 'Invalid ZIP file',
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def get_manual_instructions(self) -> str:
        """
        Get formatted manual download instructions.

        Returns:
            Formatted instructions string
        """
        return f"""
MANUAL TAXONOMY DOWNLOAD INSTRUCTIONS
{'=' * 80}

If automatic download fails, you can manually download taxonomies:

1. Download the taxonomy ZIP file from the official source

2. Place it in the manual downloads directory:
   {self.paths.manual_downloads}

3. Run the library module to process it:
   python library.py --process-manual

4. The system will:
   - Auto-detect taxonomy name and version from filename
   - Extract the taxonomy to {self.paths.taxonomies_libraries}
   - ZIP files remain in manual_downloads/ for re-processing if needed

Common taxonomy sources:
  - SEC:  https://xbrl.sec.gov/
  - FASB: https://xbrl.fasb.org/
  - IFRS: https://www.ifrs.org/
  - ESMA: https://www.esma.europa.eu/

{'=' * 80}
"""


__all__ = ['ManualProcessor']