-- Create durango user and grant permissions
CREATE USER durango WITH PASSWORD 'durangopass';
GRANT ALL PRIVILEGES ON DATABASE durango TO durango;

-- Grant schema permissions
\c durango
GRANT ALL ON SCHEMA public TO durango;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO durango;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO durango;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO durango;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO durango;
