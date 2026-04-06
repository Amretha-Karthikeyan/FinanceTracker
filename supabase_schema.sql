-- Run this in Supabase SQL Editor to create the tables
-- Go to: Supabase Dashboard → SQL Editor → New Query

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

-- Enable Row Level Security (optional but recommended)
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE savings ENABLE ROW LEVEL SECURITY;

-- Allow full access via the anon key (single-user app)
CREATE POLICY "Allow all on transactions" ON transactions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on investments" ON investments FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on savings" ON savings FOR ALL USING (true) WITH CHECK (true);
