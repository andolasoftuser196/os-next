-- Create durango database and user
CREATE USER durango WITH PASSWORD 'durangopass';
CREATE DATABASE durango OWNER durango;

-- Grant permissions on durango database
\c durango
GRANT ALL ON SCHEMA public TO durango;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO durango;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO durango;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO durango;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO durango;

-- Create orangescrum database and user
\c postgres
CREATE USER orangescrum WITH PASSWORD 'orangescrumpass';
CREATE DATABASE orangescrum OWNER orangescrum;

-- Grant permissions on orangescrum database
\c orangescrum
GRANT ALL ON SCHEMA public TO orangescrum;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO orangescrum;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO orangescrum;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO orangescrum;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO orangescrum;
