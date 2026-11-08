-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 015_alter_users_add_session_epoch.sql
-- Purpose : Password Management - server-side session invalidation.
--
--           Flask's session is a signed client-side cookie, so the server
--           has no list of sessions it could delete. Instead, every login
--           copies Users.SessionEpoch into the session, and every
--           authenticated request compares the two (app.py,
--           enforce_session_epoch). A password change or reset increments
--           SessionEpoch, which makes every previously issued session for
--           that account stale on its very next request.
--
--           Additive only: existing rows get 0, and a session issued before
--           this column existed is treated as epoch 0, so deploying this
--           migration logs nobody out.
-- =========================================================

ALTER TABLE `Users`
    ADD COLUMN `SessionEpoch` INT NOT NULL DEFAULT 0;
