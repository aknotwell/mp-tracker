# Milestone 2 schema decisions

These choices are implemented in SQLAlchemy metadata but remain changeable without data migration until Milestone 3 creates the initial Alembic revision.

- Collection items use UUID primary keys and may repeat the same user/fragrance/ownership combination. Each physical bottle or decant ranks independently.
- Users authenticate only through Google OpenID Connect. The user table stores Google's stable `sub` claim as `google_subject`, the current verified email for display/administration, and `is_admin`; it stores no password data. Login identity is matched by `google_subject`, never by email.
- Volumes use `NUMERIC(8, 2)`. Total volume must be positive; remaining volume may be zero and cannot exceed total volume.
- Depleted items remain stored. Matchup and leaderboard eligibility is query behavior for Milestone 6, not a status column.
- Attribute ratings are optional one-to-one records. If a rating exists, all three fields are required.
- Elo uses `NUMERIC(10, 4)` and starts at `1000.0000`. The exact K-factor policy remains a Milestone 5 decision.
- A scored matchup has exactly two different participants and one winner. Skipping a displayed pair does not create a scored matchup. Tie support is not included.
- Matchup audit rows snapshot both pre/post ratings, the K-factor, and an algorithm-version string. ORM update and delete operations are rejected, and foreign keys restrict deletion of referenced users/items.
- Concentration and gender are nullable normalized strings until exact product vocabularies are approved.
- Fragrance names are indexed within a house but are not unique. Concentrations, flankers, and upstream duplicates can therefore coexist until scraper identity rules are finalized.
- Automated sources may use `source_external_id` for idempotency. The pair `(data_source, source_external_id)` is unique when an external ID is present.
- Enum values are stored as constrained strings so SQLite accepts only the approved public values.
- No public fragrance-creation schema exists. The admin schema can only correct an existing row and cannot set scraper provenance or external identity.

Alembic remains the intended owner of database creation and schema upgrades. The application does not call `metadata.create_all()` on startup.
