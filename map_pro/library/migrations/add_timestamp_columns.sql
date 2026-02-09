-- ============================================================================
-- Add Missing Timestamp Columns to taxonomy_libraries
-- ============================================================================
-- Issue: Model defines timestamp columns that don't exist in physical database
-- ============================================================================

DO $$
DECLARE
    column_count INTEGER := 0;
BEGIN
    RAISE NOTICE 'Adding missing timestamp columns to taxonomy_libraries...';
    
    -- last_attempt_date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'last_attempt_date'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN last_attempt_date TIMESTAMP WITH TIME ZONE;
        COMMENT ON COLUMN taxonomy_libraries.last_attempt_date IS 'Last download/extraction attempt timestamp';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added last_attempt_date';
    ELSE
        RAISE NOTICE '  [✓] last_attempt_date already exists';
    END IF;
    
    -- last_success_date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'last_success_date'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN last_success_date TIMESTAMP WITH TIME ZONE;
        COMMENT ON COLUMN taxonomy_libraries.last_success_date IS 'Last successful download timestamp';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added last_success_date';
    ELSE
        RAISE NOTICE '  [✓] last_success_date already exists';
    END IF;
    
    -- download_completed_at
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'download_completed_at'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN download_completed_at TIMESTAMP WITH TIME ZONE;
        COMMENT ON COLUMN taxonomy_libraries.download_completed_at IS 'Download completion timestamp';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added download_completed_at';
    ELSE
        RAISE NOTICE '  [✓] download_completed_at already exists';
    END IF;
    
    -- last_verified_at
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'last_verified_at'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN last_verified_at TIMESTAMP WITH TIME ZONE;
        COMMENT ON COLUMN taxonomy_libraries.last_verified_at IS 'Last file verification timestamp';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added last_verified_at';
    ELSE
        RAISE NOTICE '  [✓] last_verified_at already exists';
    END IF;
    
    -- created_at (with default)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        COMMENT ON COLUMN taxonomy_libraries.created_at IS 'Record creation timestamp';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added created_at';
    ELSE
        RAISE NOTICE '  [✓] created_at already exists';
    END IF;
    
    -- updated_at (with default and trigger for updates)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'taxonomy_libraries' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE taxonomy_libraries ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        COMMENT ON COLUMN taxonomy_libraries.updated_at IS 'Record last update timestamp';
        column_count := column_count + 1;
        RAISE NOTICE '  [+] Added updated_at';
    ELSE
        RAISE NOTICE '  [✓] updated_at already exists';
    END IF;
    
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Migration complete: Added % timestamp columns', column_count;
    RAISE NOTICE '============================================================================';
    
END $$;

-- ============================================================================
-- Create trigger to auto-update updated_at column
-- ============================================================================

-- Create or replace the trigger function
CREATE OR REPLACE FUNCTION update_taxonomy_libraries_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if it exists (safe)
DROP TRIGGER IF EXISTS trigger_update_taxonomy_libraries_updated_at ON taxonomy_libraries;

-- Create the trigger
CREATE TRIGGER trigger_update_taxonomy_libraries_updated_at
    BEFORE UPDATE ON taxonomy_libraries
    FOR EACH ROW
    EXECUTE FUNCTION update_taxonomy_libraries_updated_at();

-- Verify
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'taxonomy_libraries'
AND column_name IN (
    'last_attempt_date', 'last_success_date', 'download_completed_at',
    'last_verified_at', 'created_at', 'updated_at'
)
ORDER BY column_name;