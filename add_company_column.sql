-- Add company_name_for_agent column to scheduled_calls table
ALTER TABLE scheduled_calls ADD COLUMN company_name_for_agent TEXT;