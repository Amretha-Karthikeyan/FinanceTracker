-- ============================================================
-- Run this in Supabase SQL Editor to create the tables
-- Go to: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- Drop existing tables if re-running
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS investments CASCADE;
DROP TABLE IF EXISTS savings CASCADE;

-- Transactions table
CREATE TABLE transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'SGD',
    category TEXT,
    source_file TEXT,
    month_year TEXT,
    type TEXT NOT NULL DEFAULT 'debit'
);

-- Investments table
CREATE TABLE investments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date DATE NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    amount NUMERIC(12,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'SGD',
    platform TEXT,
    month_year TEXT
);

-- Savings table
CREATE TABLE savings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date DATE NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    amount NUMERIC(12,2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'SGD',
    month_year TEXT
);

-- DISABLE Row Level Security (single-user app, anon key access)
-- This is the simplest setup — no RLS policies needed.
ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE investments DISABLE ROW LEVEL SECURITY;
ALTER TABLE savings DISABLE ROW LEVEL SECURITY;

-- Grant full access to anon and authenticated roles
GRANT ALL ON transactions TO anon, authenticated;
GRANT ALL ON investments TO anon, authenticated;
GRANT ALL ON savings TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
