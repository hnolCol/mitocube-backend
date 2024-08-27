-- =====================================================================================================================
-- Database Installations Scipt: ImmunoCubeV3
-- ---------------------------------------------------------------------------------------------------------------------
-- Version: 2024-06-22
-- Author: Andreas U Lindner, andreas.lindner@ukbonn.de
-- Last Change: 2024-06-01, Andreas Lindner
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

-- DROP DATABASE IF EXISTS "ImmunoCubeV3";

CREATE DATABASE "ImmunoCubeV3"
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_GB.UTF-8'
    LC_CTYPE = 'en_GB.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

-- GRANT TEMPORARY, CONNECT ON DATABASE "ImmunoCubeV3" TO PUBLIC;

\connect "ImmunoCubeV3"

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
          ENCRYPTED PASSWORD 'md514b63385e6c74d8b93884ad1d4d85e7f'; -- 'md50bd388bd3a63009cfb897fa74d5e696a';
      COMMENT ON ROLE immunocube IS 'User used by the immunocube service to access the database.';
   END IF;
END
$do$;

GRANT CONNECT ON DATABASE "ImmunoCubeV3" TO immunocube;
GRANT ALL ON DATABASE "ImmunoCubeV3" TO postgres;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT, INSERT, REFERENCES, TRIGGER, UPDATE ON TABLES TO immunocube;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT, USAGE ON SEQUENCES TO immunocube;


-- ---------------------------------------------------------------------------------------------------------------------
-- Setup (ENUM) Types
-- ---------------------------------------------------------------------------------------------------------------------

CREATE TYPE proteome_ids AS ENUM (
    'UP000005640',
    'UP000000589',
    'na'
);
ALTER TYPE proteome_ids OWNER TO postgres;


-- ---------------------------------------------------------------------------------------------------------------------
-- Setup Security
-- ---------------------------------------------------------------------------------------------------------------------

CREATE TABLE sec_permission_groups (
    id serial NOT NULL,
    label character varying NOT NULL,
    is_super_admin boolean DEFAULT false,
    -- allow_admin_datasets boolean DEFAULT false,
    -- allow_read_datasets boolean DEFAULT false,
    -- allow_submit_dataset boolean DEFAULT false,
    -- allow_admin_system boolean DEFAULT false,
    -- allow_admin_users boolean DEFAULT false,
    -- allow_login boolean DEFAULT false,
    PRIMARY KEY(id),
    UNIQUE(label)
);
ALTER TABLE sec_permission_groups OWNER TO postgres;

CREATE INDEX index_sec_permission_groups_pk ON sec_permission_groups USING btree(id);

CREATE TABLE sec_research_groups (
    id serial NOT NULL,
    research_group character varying NOT NULL,
    research_group_short character varying NOT NULL,
    institute character varying NOT NULL,
    base64_image BYTEA,
    profile_text text,
    contact_address character varying,
    contact_email character varying,
    url character varying,
    PRIMARY KEY(id),
    UNIQUE(research_group_short)
);
ALTER TABLE sec_research_groups OWNER TO postgres;

CREATE INDEX index_sec_research_groups_pk ON sec_research_groups USING btree(id);


CREATE TABLE sec_users (
    id serial NOT NULL,
    username character varying NOT NULL,
    research_group_id integer,
    firstname character varying NOT NULL,
    lastname character varying NOT NULL,
    -- orcid character varying,  -- https://orcid.org/0000-0003-1590-3547
    email character varying NOT NULL,
    email_verified boolean DEFAULT false NOT NULL,
    -- role smallint DEFAULT 0 NOT NULL,
    base64_image BYTEA,  -- https://www.base64decode.net/postgresql-decode
    -- select decode('YmFzZTY0IGVuY29kZWQgc3RyaW5n', 'base64');
    -- https://www.base64decode.net/python-base64-b64decode
    -- https://stackoverflow.com/questions/67165636/decoding-base64-encoded-image-in-flask
    -- https://stackoverflow.com/questions/3715493/encoding-an-image-file-with-base64
    -- https://www.reddit.com/r/flask/comments/mgihgl/loading_images_from_database_flask/
    -- import base64 flask io; with open(image_path, "rb") as image_file: encoded_string = base64.b64encode(image_file.read())
    -- cur.execute("INSERT INTO images (image_name, image_data) VALUES (%s, %s)", (image_name, encoded_string))
    -- @app.route('/image/<int:image_id>')
    -- def get_image(image_id):
    -- cur.execute("SELECT image_data FROM images WHERE id = %s", (image_id,))
    -- image_data = cur.fetchone()[0]
    -- image_bytes = base64.b64decode(image_data)  # Decode the base64 data
    -- image_buffer = io.BytesIO(image_bytes)  # Create an in-memory bytes buffer to hold the image data
    -- return make_response(send_file(image_buffer, mimetype='image/png'))
    profile_text text,
    orcid character varying,
    url character varying,
    allow_login boolean DEFAULT false,
    password character varying,
    personal_salt character varying,
    created_on timestamp without time zone NOT NULL,
    updated_on timestamp without time zone NOT NULL,
    last_login_on timestamp without time zone,
    expires_after timestamp without time zone NOT NULL,
    PRIMARY KEY(id),
    UNIQUE(username),
    UNIQUE(email),
    FOREIGN KEY(research_group_id) REFERENCES sec_research_groups(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE sec_users OWNER TO postgres;

CREATE INDEX index_sec_users_pk ON sec_users USING btree(id);
CREATE INDEX index_sec_users_fk ON sec_users USING btree(research_group_id);
CREATE INDEX index_sec_users_username ON sec_users USING hash(username);


CREATE TABLE sec_nm_permissions_users (
    permission_group_id integer NOT NULL,
    user_id integer NOT NULL,
    PRIMARY KEY(permission_group_id, user_id),
    FOREIGN KEY(permission_group_id) REFERENCES sec_permission_groups(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(user_id) REFERENCES sec_users(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE sec_nm_permissions_users OWNER TO postgres;

CREATE INDEX index_sec_nm_permissions_users_pk ON sec_nm_permissions_users USING btree(permission_group_id, user_id);


-- ---------------------------------------------------------------------------------------------------------------------
-- Setup Attributes
-- ---------------------------------------------------------------------------------------------------------------------

CREATE TABLE attributes (
    id serial NOT NULL,
    parent_id integer,
    tag character varying NOT NULL,
    text character varying NOT NULL,
    priority smallint DEFAULT 1000 NOT NULL,
    allow_as_filter boolean DEFAULT false NOT NULL,
    allow_for_dataset boolean DEFAULT false NOT NULL,
    allow_for_genotype boolean DEFAULT false NOT NULL,
    allow_for_performance boolean DEFAULT false NOT NULL,
    allow_for_sample boolean DEFAULT false NOT NULL,
    allow_trait_values boolean DEFAULT false NOT NULL,
    required_for_dataset_state smallint,
    PRIMARY KEY(id),
    UNIQUE(tag),
    FOREIGN KEY(parent_id) REFERENCES attributes(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE attributes OWNER TO postgres;

CREATE INDEX index_attributes_pk ON attributes USING btree(id);
CREATE INDEX index_attributes_fk ON attributes USING btree(parent_id);
CREATE INDEX index_attributes_tag ON attributes USING hash(tag);


CREATE TABLE traits (
    id serial NOT NULL,
    attribute_id integer NOT NULL,
    tag character varying NOT NULL,
    text character varying,
    keyword character varying,
    description text,
    PRIMARY KEY(id),
    UNIQUE(tag),
    UNIQUE(keyword),  -- NULLS NOT DISTINCT
    FOREIGN KEY(attribute_id) REFERENCES attributes(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE traits OWNER TO postgres;

CREATE INDEX index_traits_pk ON traits USING btree(id);
CREATE INDEX index_traits_fk ON traits USING btree(attribute_id);
CREATE INDEX index_traits_tag ON traits USING hash(tag);


-- ---------------------------------------------------------------------------------------------------------------------
-- Setup Dataset
-- ---------------------------------------------------------------------------------------------------------------------

CREATE TABLE features (
    id bigserial NOT NULL,
    label character varying NOT NULL
);
ALTER TABLE features OWNER TO postgres;


CREATE TABLE feature_pgs (
    proteome_id proteome_ids NOT NULL,
    is_grouped boolean NOT NULL,
    PRIMARY KEY(id),
    UNIQUE(label, proteome_id)
) INHERITS (features);
ALTER TABLE feature_pgs OWNER TO postgres;

CREATE INDEX index_feature_pgs_pk ON feature_pgs USING btree(id);
CREATE INDEX index_feature_pgs_label ON feature_pgs USING hash(label);


CREATE TABLE feature_pgs_nm (
    parent_pg_id bigint  NOT NULL,
    pg_id bigint NOT NULL,
    PRIMARY KEY(parent_pg_id, pg_id),
    FOREIGN KEY(parent_pg_id) REFERENCES feature_pgs(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(pg_id) REFERENCES feature_pgs(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE feature_pgs_nm OWNER TO postgres;

CREATE INDEX index_feature_pgs_nm_pk ON feature_pgs_nm USING btree(parent_pg_id, pg_id);
CREATE INDEX index_feature_pgs_nm_fk_feature_pg ON feature_pgs_nm USING btree(pg_id);


CREATE TABLE projects (
    id serial NOT NULL,
    title character varying NOT NULL,
    description character varying NOT NULL,
    PRIMARY KEY(id)
);
ALTER TABLE projects OWNER TO postgres;

CREATE INDEX index_projects_pk ON projects USING btree(id);


CREATE TABLE instruments (
    id smallserial NOT NULL,
    label character varying NOT NULL,
    name character varying NOT NULL,
    location character varying,
    description character varying,
    base64_image BYTEA,
    PRIMARY KEY(id),
    UNIQUE(label)
);
ALTER TABLE instruments OWNER TO postgres;

CREATE INDEX index_instruments_pk ON instruments USING btree(id);


CREATE TABLE datasets (
    id serial NOT NULL,
    instrument_id smallint,
    project_id integer NOT NULL,
    label character varying NOT NULL,
    created_on timestamp without time zone NOT NULL,
    uploaded_on timestamp without time zone DEFAULT now() NOT NULL,
    title character varying NOT NULL,
    contact_email character varying,
    user_id integer,
    research_group_id integer,
    state smallint DEFAULT 0 NOT NULL,
    PRIMARY KEY(id),
    UNIQUE(label),
    FOREIGN KEY(instrument_id) REFERENCES instruments(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(user_id) REFERENCES sec_users(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(research_group_id) REFERENCES sec_research_groups(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE datasets OWNER TO postgres;

CREATE INDEX index_datasets_pk ON datasets USING btree(id);
CREATE INDEX index_datasets_fk_instrument ON datasets USING btree(instrument_id);
CREATE INDEX index_datasets_fk_project ON datasets USING btree(project_id);
CREATE INDEX index_datasets_fk_user ON datasets USING btree(user_id);
CREATE INDEX index_datasets_fk_research_group ON datasets USING btree(research_group_id);
CREATE INDEX index_datasets_label ON datasets USING hash(label);


CREATE TABLE samples (
    id bigserial NOT NULL,
    dataset_id integer NOT NULL,
    label character varying NOT NULL,
    PRIMARY KEY(id),
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE samples OWNER TO postgres;

CREATE INDEX index_samples_pk ON samples USING btree(id);
CREATE INDEX index_samples_fk ON samples USING btree(dataset_id);


CREATE TABLE sample_replicates (
    sample_id bigint NOT NULL,
    replicate_label character varying NOT NULL,  -- Question, extra replicate table?
    PRIMARY KEY(sample_id),
    FOREIGN KEY(sample_id) REFERENCES samples(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE sample_replicates OWNER TO postgres;

CREATE INDEX index_sample_replicates_pk ON sample_replicates USING btree(sample_id);


CREATE TABLE sample_batches (
    sample_id bigint NOT NULL,
    batch_label character varying NOT NULL,  -- Question, extra batch table?
    PRIMARY KEY(sample_id),
    FOREIGN KEY(sample_id) REFERENCES samples(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE sample_batches OWNER TO postgres;

CREATE INDEX index_sample_batches_pk ON sample_batches USING btree(sample_id);

CREATE TABLE feature_values (
    dataset_id integer NOT NULL,
    sample_id bigint NOT NULL,
    feature_id bigint NOT NULL,
    feature_value real NOT NULL
);
ALTER TABLE feature_values OWNER TO postgres;


CREATE TABLE feature_pg_values (
    PRIMARY KEY(sample_id, feature_id),
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(sample_id) REFERENCES samples(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(feature_id) REFERENCES feature_pgs(id) ON UPDATE CASCADE ON DELETE RESTRICT
) INHERITS (feature_values);
ALTER TABLE feature_pg_values OWNER TO postgres;

CREATE INDEX index_feature_values_pk ON feature_pg_values USING btree(sample_id, feature_id);
CREATE INDEX index_feature_values_fk_user ON feature_pg_values USING btree(feature_id);
CREATE INDEX index_feature_values_fk_project ON feature_pg_values USING btree(dataset_id);


-- ---------------------------------------------------------------------------------------------------------------------
-- Setup Dataset - Extras
-- ---------------------------------------------------------------------------------------------------------------------

CREATE TABLE metatexts (
    dataset_id integer NOT NULL,
    tag character varying NOT NULL,
    text text NOT NULL,
    PRIMARY KEY(dataset_id, tag),
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE metatexts OWNER TO postgres;

CREATE INDEX index_metatexts_pk ON metatexts USING btree(dataset_id, tag);


CREATE TABLE dataset_urls (
    dataset_id integer NOT NULL,
    url character varying NOT NULL,
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON UPDATE CASCADE ON DELETE RESTRICT
);
ALTER TABLE dataset_urls OWNER TO postgres;

CREATE INDEX index_dataset_urls_fk ON dataset_urls USING btree(dataset_id);


-- ---------------------------------------------------------------------------------------------------------------------
-- Setup Timelines
-- ---------------------------------------------------------------------------------------------------------------------

CREATE TABLE timeline_events (
    id bigserial NOT NULL,
    event_on timestamp without time zone NOT NULL,
    created_by integer,
    state character varying NOT NULL,
    comment character varying
);
ALTER TABLE timeline_events OWNER TO postgres;


CREATE TABLE dataset_timeline_events (
    dataset_id integer NOT NULL,
    type character varying NOT NULL,
    PRIMARY KEY(id),
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON UPDATE CASCADE ON DELETE RESTRICT
) INHERITS (timeline_events);
ALTER TABLE dataset_timeline_events OWNER TO postgres;

CREATE INDEX index_dataset_timeline_events_pk ON dataset_timeline_events USING btree(id);
CREATE INDEX index_dataset_timeline_events_fk ON dataset_timeline_events USING btree(dataset_id);

-- ---------------------------------------------------------------------------------------------------------------------
-- Setup NM Attributes - xyz
-- ---------------------------------------------------------------------------------------------------------------------

CREATE TABLE nm_traits (
    trait_id serial NOT NULL,
    trait_value character varying,
    trait_unit character varying
);
ALTER TABLE nm_traits OWNER TO postgres;

CREATE TABLE nm_traits_datasets (
    dataset_id integer NOT NULL,
    PRIMARY KEY(trait_id, dataset_id),
    FOREIGN KEY(trait_id) REFERENCES traits(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON UPDATE CASCADE ON DELETE RESTRICT
) INHERITS (nm_traits);
ALTER TABLE nm_traits_datasets OWNER TO postgres;

CREATE INDEX index_nm_traits_datasets_pk ON nm_traits_datasets USING btree(trait_id, dataset_id);
CREATE INDEX index_nm_traits_datasets_fk_dataset ON nm_traits_datasets USING btree(dataset_id);


CREATE TABLE nm_traits_samples (
    sample_id integer NOT NULL,
    PRIMARY KEY(trait_id, sample_id),
    FOREIGN KEY(trait_id) REFERENCES traits(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(sample_id) REFERENCES samples(id) ON UPDATE CASCADE ON DELETE RESTRICT
) INHERITS (nm_traits);
ALTER TABLE nm_traits_samples OWNER TO postgres;

CREATE INDEX index_nm_traits_samples_pk ON nm_traits_samples USING btree(trait_id, sample_id);
CREATE INDEX index_nm_traits_samples_fk_sample ON nm_traits_samples USING btree(sample_id);


-- ---------------------------------------------------------------------------------------------------------------------
-- Genotype
-- ---------------------------------------------------------------------------------------------------------------------

CREATE TABLE genotypes (
    id serial NOT NULL,
    name character varying NOT NULL,
    description character varying,
    is_selectable boolean DEFAULT false,
    created_by integer,
    created_on timestamp without time zone NOT NULL,
    PRIMARY KEY(id),
    UNIQUE(name)
);
ALTER TABLE genotypes OWNER TO postgres;

CREATE INDEX index_genotypes_pk ON genotypes USING btree(id);
CREATE INDEX index_genotypes_proteome_id ON genotypes USING btree(proteome_id);
CREATE INDEX index_genotypes_name ON genotypes USING hash(name);

CREATE TABLE nm_genotypes (
    genotype_id serial NOT NULL
);
ALTER TABLE nm_genotypes OWNER TO postgres;

CREATE TABLE nm_genotypes_datasets (
    dataset_id integer NOT NULL,
    PRIMARY KEY(genotype_id, dataset_id),
    FOREIGN KEY(genotype_id) REFERENCES genotypes(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON UPDATE CASCADE ON DELETE RESTRICT
) INHERITS (nm_genotypes);
ALTER TABLE nm_genotypes_datasets OWNER TO postgres;

CREATE INDEX index_nm_genotypes_datasets_pk ON nm_genotypes_datasets USING btree(genotype_id, dataset_id);
CREATE INDEX index_nm_genotypes_datasets_fk_dataset ON nm_genotypes_datasets USING btree(dataset_id);


CREATE TABLE nm_genotypes_samples (
    sample_id integer NOT NULL,
    PRIMARY KEY(genotype_id, sample_id),
    FOREIGN KEY(genotype_id) REFERENCES genotypes(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(sample_id) REFERENCES samples(id) ON UPDATE CASCADE ON DELETE RESTRICT
) INHERITS (nm_genotypes);
ALTER TABLE nm_genotypes_samples OWNER TO postgres;

CREATE INDEX index_nm_genotypes_samples_pk ON nm_genotypes_samples USING btree(genotype_id, sample_id);
CREATE INDEX index_nm_genotypes_samples_fk_sample ON nm_genotypes_samples USING btree(sample_id);


CREATE TABLE nm_genotypes_pg_traits (
    trait_id integer NOT NULL,
    feature_id bigint,
    proteome_id proteome_ids NOT NULL,
    genotype_value character varying,
    PRIMARY KEY(genotype_id, trait_id),
    FOREIGN KEY(genotype_id) REFERENCES genotypes(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY(trait_id) REFERENCES traits(id) ON UPDATE CASCADE ON DELETE RESTRICT
) INHERITS (nm_genotypes);
ALTER TABLE nm_genotypes_traits OWNER TO postgres;

CREATE INDEX index_nm_genotypes_traits_pk ON nm_genotypes_traits USING btree(genotype_id, trait_id);
CREATE INDEX index_nm_genotypes_traits_fk_trait_id ON nm_genotypes_traits USING btree(trait_id);


-- ---------------------------------------------------------------------------------------------------------------------
-- Setup Functions
-- ---------------------------------------------------------------------------------------------------------------------

CREATE FUNCTION get_db_size_bytes() RETURNS integer
    LANGUAGE plpgsql
    AS $$DECLARE
	size_in_bytes integer;
BEGIN
	SELECT pg_database_size('ImmunoCubeV3') INTO size_in_bytes;
	--SELECT 	pg_database_size('ImmunoCubeV2') -
	--	pg_total_relation_size('sec_tokens') -
	--	pg_total_relation_size('sec_users') -
	--	pg_total_relation_size('nm_users_attribute_value')
	-- 	INTO size_in_bytes;
	RETURN size_in_bytes;
END;
$$;
ALTER FUNCTION get_db_size_bytes() OWNER TO postgres;
