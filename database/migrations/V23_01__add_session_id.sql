-- ============================================================
-- Migration V23.01: Add session_id to ai_chat_history
-- ============================================================

ALTER TABLE ai_chat_history 
ADD COLUMN session_id VARCHAR(255) AFTER user_id,
ADD INDEX idx_aich_session (session_id);

-- Note: This migration is idempotent only if column doesn't exist.
-- Use: IF NOT EXISTS is not supported for ALTER TABLE ADD COLUMN in MySQL.
-- Run only once or check column existence first:
--   SELECT COUNT(*) FROM information_schema.COLUMNS 
--   WHERE TABLE_SCHEMA = 'hdbhms' AND TABLE_NAME = 'ai_chat_history' AND COLUMN_NAME = 'session_id';
