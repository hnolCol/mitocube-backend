-- =====================================================================================================================
-- Database Installations Scipt: ImmunoCubeV4
-- ---------------------------------------------------------------------------------------------------------------------
-- Setup / Creation of the database itself without tables
-- ---------------------------------------------------------------------------------------------------------------------
-- Version: 2024-11-27
-- Author: Andreas U Lindner, andreas.lindner@ukbonn.de
-- Last Change: 2024-11-27, Andreas Lindner
-- Target DB: postgreSQL 12.17, Ubuntu
-- =====================================================================================================================

-- CREATE INDEX index_xxx_id ON abc USING btree(id);
-- CREATE INDEX index_nm_xxx ON abc USING btree(a_id, b_id);
-- CREATE INDEX index_xxx ON abc USING hash(tag);
-- CREATE INDEX index_xxx ON abc USING GIST(compareme);
-- CREATE INDEX index_xxx ON abc USING GIST(text_or_time);
-- CREATE INDEX index_xxx ON abc USING BRIN(time_or_ordered);

-- ---------------------------------------------------------------------------------------------------------------------
-- Setup Database
-- ---------------------------------------------------------------------------------------------------------------------

-- DROP DATABASE IF EXISTS "ImmunoCubeV4";

CREATE DATABASE "ImmunoCubeV5"
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_GB.UTF-8'
    LC_CTYPE = 'en_GB.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

-- GRANT TEMPORARY, CONNECT ON DATABASE "ImmunoCubeV4" TO PUBLIC;

\connect "ImmunoCubeV5"

-- ---------------------------------------------------------------------------------------------------------------------
-- Install extensions
-- ---------------------------------------------------------------------------------------------------------------------
-- SELECT * FROM pg_available_extensions;  -- Check for available extensions
CREATE EXTENSION pgcrypto;  -- requires 'sudo apt-get install postgresql-contrib'

-- ---------------------------------------------------------------------------------------------------------------------
-- Setup Rights
-- ---------------------------------------------------------------------------------------------------------------------

DO
$do$
BEGIN
   IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'immunocube') THEN
      RAISE NOTICE 'Role "immunocube" already exists. Skipping.';
   ELSE
      CREATE ROLE immunocube WITH
          LOGIN
          NOSUPERUSER
          INHERIT
          NOCREATEDB
          NOCREATEROLE
          NOREPLICATION
          NOBYPASSRLS
          ENCRYPTED PASSWORD 'md514b63385e6c74d8b93884ad1d4d85e7f'; -- 'md50bd388bd3a63009cfb897fa74d5e696a';  ---- jflw$4Uv%9j8X4?jpeXuXYZgjpr!de2
      COMMENT ON ROLE immunocube IS 'User used by the immunocube service to access the database.';
   END IF;
END
$do$;

GRANT CONNECT ON DATABASE "ImmunoCubeV5" TO immunocube;
GRANT ALL ON DATABASE "ImmunoCubeV5" TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT, INSERT, REFERENCES, TRIGGER, UPDATE ON TABLES TO immunocube;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT, USAGE ON SEQUENCES TO immunocube;
