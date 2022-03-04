CREATE TABLE modreports (
    id SERIAL PRIMARY KEY,
    reporter BIGINT NOT NULL,
    target BIGINT NOT NULL, -- the user in question
    reportRemarks TEXT, -- the remarks sent with the report. could be None if there were no remarks

    channel BIGINT, -- when targeting a message, these two will be populated
    message BIGINT,

    reportMessage BIGINT, -- the message in the report channel, for persistent views

    mod BIGINT, -- the mod who responded to the report
    modAction TEXT, -- the action taken. Automatically generated
    modRemarks TEXT,
    modResponse TEXT
);
CREATE TABLE tags_new (
    id SERIAL UNIQUE,
    name TEXT NOT NULL CHECK (char_length(name) <= 32),
    PRIMARY KEY (name),
    content TEXT NOT NULL CHECK (char_length(content) <= 2000),
    owner BIGINT NOT NULL,
    uses INT DEFAULT 0,
    created TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc')
);
CREATE TABLE tag_lookup (
    name TEXT PRIMARY KEY CHECK (char_length(name) <= 32),
    tagId INT NOT NULL REFERENCES tags_new(id),
    isAlias BOOLEAN NOT NULL
);

CREATE FUNCTION isTagOwner(tagID_ INTEGER, requester BIGINT)
    RETURNS BOOLEAN
    LANGUAGE plpgsql
    AS
    $$
    BEGIN
        IF ((
            SELECT 1
                FROM tags_new
                WHERE
                    owner = requester AND id = tagID_
            ) IS NULL
        )
        THEN RETURN FALSE;
        END IF;
        RETURN TRUE;
    END
    $$;

CREATE FUNCTION findTag(givenName TEXT)
    RETURNS TEXT[] -- [name, content]
    LANGUAGE plpgsql
    AS
    $$
    DECLARE
        tagID_ INT;
        tagName TEXT;
        tagContent TEXT;
    BEGIN
        SELECT tagId
            INTO tagID_
            FROM tag_lookup
            WHERE name = givenName;

        IF tagID_ IS NULL
            THEN RETURN NULL;
        END IF;

        UPDATE tags_new
            SET uses = uses + 1
            WHERE id = tagID_
            RETURNING name, content
                INTO tagName, tagContent;

        RETURN ARRAY[tagName, tagContent];
    END
    $$;

CREATE FUNCTION createTag (tag_name TEXT, tag_content TEXT, tag_owner BIGINT)
    RETURNS INT
    LANGUAGE plpgsql
    AS
    $$
    DECLARE
        tagID_ INT;
    BEGIN
        INSERT INTO
            tags_new (name, content, owner)
            VALUES (tag_name, tag_content, tag_owner)
            RETURNING id INTO tagID_;
        INSERT INTO
            tag_lookup (name, tagId, isAlias)
            VALUES (tag_name, tagID_, FALSE);
        RETURN tagID_;
    END
    $$;

CREATE FUNCTION createAlias (originalTag TEXT, aliasName TEXT)
    RETURNS TEXT
    LANGUAGE plpgsql
    AS
    $$
    DECLARE
        tagID_ INT;
        tagName TEXT;
    BEGIN
        SELECT
            tagId, name
            INTO tagID_, tagName
            FROM tag_lookup
            WHERE name = originalTag;

        IF (tagID_ IS NULL)
            THEN RETURN "Tag does not exist";
        END IF;

        INSERT INTO
            tag_lookup (name, tagId, isAlias)
            VALUES (aliasName, tagID_, TRUE);

        RETURN concat("Created alias ", aliasName, " that points to ", tagName);
    END
    $$;

CREATE FUNCTION deleteTag (tagName TEXT, requester BIGINT)
    RETURNS TEXT
    LANGUAGE plpgsql
    AS
    $$
    DECLARE
        tagID_ INT;
        isAlias_ BOOLEAN;
    BEGIN
        SELECT
            tagId, isAlias
            INTO tagID_, isAlias_
            FROM tag_lookup
            WHERE name = tagName;

        IF (isTagOwner(tagID_, requester) IS FALSE)
        THEN RETURN "You do not own this tag";
        END IF;

        IF (isAlias_ IS FALSE)
            THEN
                DELETE FROM tag_lookup WHERE tagId = tagID_;
                DELETE FROM tags_new WHERE id = tagID_;
                RETURN "Tag deleted";
        END IF;
        IF (isAlias_ IS TRUE)
            THEN
                DELETE FROM tag_lookup WHERE name = tagName;
                RETURN "Tag alias deleted";
        END IF;
    END
    $$;