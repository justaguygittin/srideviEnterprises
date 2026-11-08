-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 016_create_passwordresettokens.sql
-- Purpose : Password Management - single-use, time-limited reset tokens.
--
--           TokenHash is the SHA-256 (hex) of a 32-byte random token from
--           secrets.token_urlsafe(). The raw token exists only in the email
--           sent to the account holder; it is never stored or logged.
--           A fast hash is appropriate here (unlike passwords) because the
--           token carries 256 bits of entropy and cannot be guessed.
--
--           All timestamps are UTC (written with UTC_TIMESTAMP()), so token
--           expiry does not depend on the server's or MariaDB's time zone.
--
--           UserRole records the account's role when the token was issued.
--           Redeeming a token requires Users.Role to still match, so an
--           Employee token can never reset an Admin account (and vice versa)
--           even if a role changes while a token is outstanding.
--
--           InitiatedByUserID is NULL for a self-service "Forgot password"
--           request, and the Admin's UserID for an Admin-assisted reset -
--           this doubles as the audit trail for Admin-initiated resets.
-- =========================================================

CREATE TABLE `PasswordResetTokens` (
    `TokenID` INT AUTO_INCREMENT PRIMARY KEY,
    `UserID` INT NOT NULL,
    `UserRole` VARCHAR(20) NOT NULL,
    `TokenHash` CHAR(64) NOT NULL,
    `ExpiresAt` DATETIME NOT NULL,
    `UsedAt` DATETIME NULL,
    `RevokedAt` DATETIME NULL,
    `CreatedAt` DATETIME NOT NULL,
    `InitiatedByUserID` INT NULL,

    CONSTRAINT `uq_passwordresettokens_tokenhash` UNIQUE (`TokenHash`),
    CONSTRAINT `fk_passwordresettokens_userid` FOREIGN KEY (`UserID`) REFERENCES `Users` (`UserID`),
    CONSTRAINT `fk_passwordresettokens_initiatedby` FOREIGN KEY (`InitiatedByUserID`) REFERENCES `Users` (`UserID`),

    INDEX `idx_passwordresettokens_user_created` (`UserID`, `CreatedAt`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
