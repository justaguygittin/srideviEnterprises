-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 020_create_invoicenumberaudit.sql
-- Purpose : Admin Invoice Number Configuration - audit trail of every
--           change an Admin makes to InvoiceNumberSequence.NextNumber.
--
--           One row per accepted change, written in the same transaction as
--           the change itself. HighestIssued records the highest
--           InvoiceNumber that existed at the time (0 if none), so the
--           history shows the gap the Admin deliberately introduced.
--           ChangedAt is UTC (UTC_TIMESTAMP()). Rows are never updated or
--           deleted by the application.
-- =========================================================

CREATE TABLE IF NOT EXISTS `InvoiceNumberAudit` (
    `AuditID` INT AUTO_INCREMENT PRIMARY KEY,
    `AdminUserID` INT NOT NULL,
    `OldNextNumber` INT NOT NULL,
    `NewNextNumber` INT NOT NULL,
    `HighestIssued` INT NOT NULL,
    `ChangedAt` DATETIME NOT NULL,

    CONSTRAINT `fk_invoicenumberaudit_adminuserid` FOREIGN KEY (`AdminUserID`) REFERENCES `Users` (`UserID`),

    INDEX `idx_invoicenumberaudit_changedat` (`ChangedAt`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
