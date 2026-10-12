-- V1: Initial schema — app v1.0
-- Users table stores full name as a single column.

CREATE TABLE users (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    email      VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed some v1 data
INSERT INTO users (name, email) VALUES
    ('Sarah Connor',   'sarah@example.com'),
    ('John Connor',    'john@example.com'),
    ('Miles Dyson',    'miles@example.com');
