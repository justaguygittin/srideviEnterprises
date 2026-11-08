-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 017_create_auththrottle.sql
-- Purpose : Password Management - database-backed rate limiting for login
--           and password-recovery endpoints.
--
--           Stored in the database rather than in memory because HostyCare
--           runs several Passenger worker processes at once; a per-process
--           counter would let an attacker multiply every limit by the number
--           of workers.
--
--           KeyHash is SHA-256 of "<action>:<subject>" where the subject is
--           a client IP, a lower-cased username/email, or a UserID. No raw
--           IP address, username or email is stored. Rows older than one
--           day are deleted opportunistically by services/password_service.py.
--           CreatedAt is UTC (UTC_TIMESTAMP()).
-- =========================================================

CREATE TABLE `AuthThrottle` (
    `ThrottleID` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `Action` VARCHAR(30) NOT NULL,
    `KeyHash` CHAR(64) NOT NULL,
    `CreatedAt` DATETIME NOT NULL,

    INDEX `idx_auththrottle_lookup` (`Action`, `KeyHash`, `CreatedAt`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
