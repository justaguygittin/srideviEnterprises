-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 019_create_invoicenumbersequence.sql
-- Purpose : Admin Invoice Number Configuration - the single-row sequence
--           that hands out customer-visible invoice numbers.
--
--           NextNumber is the number the next SUCCESSFUL invoice receives.
--           services/invoice_service.py:create_invoice() reads it with
--           SELECT ... FOR UPDATE inside the same transaction that inserts
--           the invoice, then increments it - so concurrent invoices queue
--           on this row and a failed (rolled-back) invoice never consumes a
--           number.
--
--           Admins can only move NextNumber UP, and only above the highest
--           number already issued (/admin/invoice-numbering); every change is
--           written to InvoiceNumberAudit (020).
--
--           Seeded from the highest existing InvoiceNumber (018 must run
--           first), so the sequence continues exactly where existing
--           invoices left off - 1 on an empty table. INSERT IGNORE makes a
--           re-run a no-op: it never resets a sequence that is already live.
--
--           The CHECK on SequenceID keeps this table to exactly one row.
--           NextNumber may reach 100000000 (one past the maximum invoice
--           number 99,999,999); the application refuses to issue it.
-- =========================================================

CREATE TABLE IF NOT EXISTS `InvoiceNumberSequence` (
    `SequenceID` TINYINT NOT NULL PRIMARY KEY,
    `NextNumber` INT NOT NULL,
    `UpdatedAt` DATETIME NOT NULL,

    CONSTRAINT `chk_invoicenumbersequence_single_row` CHECK (`SequenceID` = 1),
    CONSTRAINT `chk_invoicenumbersequence_range` CHECK (`NextNumber` BETWEEN 1 AND 100000000)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

INSERT IGNORE INTO `InvoiceNumberSequence` (`SequenceID`, `NextNumber`, `UpdatedAt`)
SELECT 1, COALESCE(MAX(`InvoiceNumber`), 0) + 1, UTC_TIMESTAMP()
FROM `Invoices`;
