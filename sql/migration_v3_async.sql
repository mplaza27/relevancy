-- Migration v3: Add keywords column to upload_sessions (for async processing)
-- Run this in the Supabase SQL Editor before deploying the async upload changes.

ALTER TABLE upload_sessions ADD COLUMN IF NOT EXISTS keywords TEXT[] DEFAULT '{}';
