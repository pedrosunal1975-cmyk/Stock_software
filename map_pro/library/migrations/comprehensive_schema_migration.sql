-- ============================================================================
-- Comprehensive Database Migration: Add ALL Missing Columns
-- ============================================================================
-- Table: taxonomy_libraries
-- Issue: Model defines many columns that don't exist in physical database
-- This adds all missing columns with proper defaults and comments
-- ============================================================================

DO $$
DECLARE
    column_count INTEGER := 0;
BEGIN
    RAISE NOTICE 'Starting taxonomy_libraries schema migration...';
    
    -- ========================================================================
    -- DOWNLOAD URLS
    -- ========================================================================
    
    -- primary_url (already added, but check anyway)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'primary_url'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN primary_url TEXT;
        COMMENT ON COLUMN taxonomy_libraries.primary_url IS 'Primary download URL (original)';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added primary_url';
    ELSE
        RAISE NOTICE '  [âœ"] primary_url already exists';
    END IF;
    
    -- current_url
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'current_url'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN current_url TEXT;
        COMMENT ON COLUMN taxonomy_libraries.current_url IS 'Currently trying URL';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added current_url';
    ELSE
        RAISE NOTICE '  [âœ"] current_url already exists';
    END IF;
    
    -- alternative_urls_tried
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'alternative_urls_tried'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN alternative_urls_tried JSONB DEFAULT '[]'::jsonb;
        COMMENT ON COLUMN taxonomy_libraries.alternative_urls_tried IS 'List of alternative URLs attempted';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added alternative_urls_tried';
    ELSE
        RAISE NOTICE '  [âœ"] alternative_urls_tried already exists';
    END IF;
    
    -- ========================================================================
    -- FILE SYSTEM PATHS
    -- ========================================================================
    
    -- downloaded_file_path
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'downloaded_file_path'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN downloaded_file_path TEXT;
        COMMENT ON COLUMN taxonomy_libraries.downloaded_file_path IS 'Path to downloaded ZIP file';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added downloaded_file_path';
    ELSE
        RAISE NOTICE '  [âœ"] downloaded_file_path already exists';
    END IF;
    
    -- downloaded_file_size
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'downloaded_file_size'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN downloaded_file_size INTEGER;
        COMMENT ON COLUMN taxonomy_libraries.downloaded_file_size IS 'Downloaded file size in bytes';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added downloaded_file_size';
    ELSE
        RAISE NOTICE '  [âœ"] downloaded_file_size already exists';
    END IF;
    
    -- expected_file_size
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'expected_file_size'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN expected_file_size INTEGER;
        COMMENT ON COLUMN taxonomy_libraries.expected_file_size IS 'Expected file size in bytes';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added expected_file_size';
    ELSE
        RAISE NOTICE '  [âœ"] expected_file_size already exists';
    END IF;
    
    -- extraction_path
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'extraction_path'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN extraction_path TEXT;
        COMMENT ON COLUMN taxonomy_libraries.extraction_path IS 'Path where files were extracted';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added extraction_path';
    ELSE
        RAISE NOTICE '  [âœ"] extraction_path already exists';
    END IF;
    
    -- ========================================================================
    -- FILE VERIFICATION
    -- ========================================================================
    
    -- file_count
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'file_count'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN file_count INTEGER DEFAULT 0;
        COMMENT ON COLUMN taxonomy_libraries.file_count IS 'Number of files extracted (new tracking)';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added file_count';
    ELSE
        RAISE NOTICE '  [âœ"] file_count already exists';
    END IF;
    
    -- ========================================================================
    -- STATUS TRACKING
    -- ========================================================================
    
    -- status (overall status)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'status'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN status VARCHAR(50) DEFAULT 'pending';
        COMMENT ON COLUMN taxonomy_libraries.status IS 'Overall status: pending, active, inactive, failed';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added status';
    ELSE
        RAISE NOTICE '  [âœ"] status already exists';
    END IF;
    
    -- validation_status
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'validation_status'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN validation_status VARCHAR(50) DEFAULT 'pending';
        COMMENT ON COLUMN taxonomy_libraries.validation_status IS 'Validation status: pending, valid, incomplete, corrupted';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added validation_status';
    ELSE
        RAISE NOTICE '  [âœ"] validation_status already exists';
    END IF;
    
    -- ========================================================================
    -- ATTEMPT TRACKING
    -- ========================================================================
    
    -- download_attempts
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'download_attempts'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN download_attempts INTEGER DEFAULT 0;
        COMMENT ON COLUMN taxonomy_libraries.download_attempts IS 'Number of download attempts';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added download_attempts';
    ELSE
        RAISE NOTICE '  [âœ"] download_attempts already exists';
    END IF;
    
    -- extraction_attempts
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'extraction_attempts'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN extraction_attempts INTEGER DEFAULT 0;
        COMMENT ON COLUMN taxonomy_libraries.extraction_attempts IS 'Number of extraction attempts';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added extraction_attempts';
    ELSE
        RAISE NOTICE '  [âœ"] extraction_attempts already exists';
    END IF;
    
    -- total_attempts
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'total_attempts'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN total_attempts INTEGER DEFAULT 0;
        COMMENT ON COLUMN taxonomy_libraries.total_attempts IS 'Total attempts (download + extraction)';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added total_attempts';
    ELSE
        RAISE NOTICE '  [âœ"] total_attempts already exists';
    END IF;
    
    -- ========================================================================
    -- FAILURE TRACKING
    -- ========================================================================
    
    -- failure_stage
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'failure_stage'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN failure_stage VARCHAR(50);
        COMMENT ON COLUMN taxonomy_libraries.failure_stage IS 'Failure stage: download, extraction, validation';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added failure_stage';
    ELSE
        RAISE NOTICE '  [âœ"] failure_stage already exists';
    END IF;
    
    -- failure_reason
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'failure_reason'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN failure_reason VARCHAR(50);
        COMMENT ON COLUMN taxonomy_libraries.failure_reason IS 'Specific failure reason code';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added failure_reason';
    ELSE
        RAISE NOTICE '  [âœ"] failure_reason already exists';
    END IF;
    
    -- failure_details
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'failure_details'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN failure_details TEXT;
        COMMENT ON COLUMN taxonomy_libraries.failure_details IS 'Full error message and details';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added failure_details';
    ELSE
        RAISE NOTICE '  [âœ"] failure_details already exists';
    END IF;
    
    -- ========================================================================
    -- SUMMARY
    -- ========================================================================
    
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Migration complete: Added % new columns', column_count;
    RAISE NOTICE '============================================================================';
    
END $$;

-- ============================================================================
-- VERIFY ALL COLUMNS
-- ============================================================================

SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'taxonomy_libraries'
AND column_name IN (
    'primary_url', 'current_url', 'alternative_urls_tried',
    'downloaded_file_path', 'downloaded_file_size', 'expected_file_size', 'extraction_path',
    'file_count', 'status', 'validation_status',
    'download_attempts', 'extraction_attempts', 'total_attempts',
    'failure_stage', 'failure_reason', 'failure_details'
)
ORDER BY column_name;