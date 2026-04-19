-- ============================================================
-- MIGRATION: Add user authentication & per-user data isolation
-- Run this in Supabase SQL Editor AFTER enabling Auth
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- Step 1: Add user_id column to all tables
-- ────────────────────────────────────────────────────────────

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

ALTER TABLE investments
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

ALTER TABLE savings
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

-- ────────────────────────────────────────────────────────────
-- Step 2: Enable Row Level Security on all tables
-- ────────────────────────────────────────────────────────────

ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings ENABLE ROW LEVEL SECURITY;

-- ────────────────────────────────────────────────────────────
-- Step 3: Drop old permissive policies if they exist
-- ────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS "Users can view own transactions" ON transactions;
DROP POLICY IF EXISTS "Users can insert own transactions" ON transactions;
DROP POLICY IF EXISTS "Users can update own transactions" ON transactions;
DROP POLICY IF EXISTS "Users can delete own transactions" ON transactions;

DROP POLICY IF EXISTS "Users can view own investments" ON investments;
DROP POLICY IF EXISTS "Users can insert own investments" ON investments;
DROP POLICY IF EXISTS "Users can update own investments" ON investments;
DROP POLICY IF EXISTS "Users can delete own investments" ON investments;

DROP POLICY IF EXISTS "Users can view own savings" ON savings;
DROP POLICY IF EXISTS "Users can insert own savings" ON savings;
DROP POLICY IF EXISTS "Users can update own savings" ON savings;
DROP POLICY IF EXISTS "Users can delete own savings" ON savings;

-- ────────────────────────────────────────────────────────────
-- Step 4: Create RLS policies — each user sees only their data
-- ────────────────────────────────────────────────────────────

-- Transactions
CREATE POLICY "Users can view own transactions"
    ON transactions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own transactions"
    ON transactions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own transactions"
    ON transactions FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own transactions"
    ON transactions FOR DELETE
    USING (auth.uid() = user_id);

-- Investments
CREATE POLICY "Users can view own investments"
    ON investments FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own investments"
    ON investments FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own investments"
    ON investments FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own investments"
    ON investments FOR DELETE
    USING (auth.uid() = user_id);

-- Savings
CREATE POLICY "Users can view own savings"
    ON savings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own savings"
    ON savings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own savings"
    ON savings FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own savings"
    ON savings FOR DELETE
    USING (auth.uid() = user_id);

-- ────────────────────────────────────────────────────────────
-- Step 5: Grant access to authenticated role
-- ────────────────────────────────────────────────────────────

GRANT SELECT, INSERT, UPDATE, DELETE ON transactions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON investments TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON savings TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Revoke anon access (only authenticated users can access data)
REVOKE ALL ON transactions FROM anon;
REVOKE ALL ON investments FROM anon;
REVOKE ALL ON savings FROM anon;

-- ────────────────────────────────────────────────────────────
-- NOTES:
-- ────────────────────────────────────────────────────────────
-- • Existing rows without user_id will be invisible to all users.
--   To migrate old data, UPDATE ... SET user_id = '<your-user-uuid>';
-- • Email confirmation: In Supabase Dashboard → Authentication → Settings,
--   you can disable "Enable email confirmations" for easier testing.
-- • The app sends user_id on every INSERT so RLS policies pass.
