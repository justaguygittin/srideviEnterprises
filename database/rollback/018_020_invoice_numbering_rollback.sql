-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 018_020_invoice_numbering_rollback.sql
-- Purpose : Emergency rollback of migrations 018-020 (Admin Invoice Number
--           Configuration), for use ONLY together with redeploying the
--           previous application code.
--
--           Deliberately kept OUTSIDE database/schema/ so it is never
--           imported as part of a fresh install.
--
--           !! SAFE ONLY WHILE EVERY INVOICE STILL HAS InvoiceNumber = InvoiceID !!
--           The previous code prints InvoiceID as the invoice number. Once an
--           Admin has moved the sequence (or any invoice was issued after a
--           move), dropping InvoiceNumber would silently change the printed
--           number of those invoices. Run this check first - it MUST return 0:
--
--             SELECT COUNT(*) FROM Invoices WHERE InvoiceNumber <> InvoiceID;
--
--           If it returns anything else, do NOT roll back: restore from the
--           pre-migration backup instead, or keep the new code.
-- =========================================================

DROP TABLE IF EXISTS `InvoiceNumberAudit`;
DROP TABLE IF EXISTS `InvoiceNumberSequence`;

ALTER TABLE `Invoices`
    DROP INDEX IF EXISTS `uq_invoices_invoicenumber`,
    DROP COLUMN IF EXISTS `InvoiceNumber`;
