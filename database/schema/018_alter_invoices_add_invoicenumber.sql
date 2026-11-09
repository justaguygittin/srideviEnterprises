-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 018_alter_invoices_add_invoicenumber.sql
-- Purpose : Admin Invoice Number Configuration - separates the
--           customer-visible invoice number from the internal primary key.
--
--           InvoiceID stays the internal AUTO_INCREMENT primary key (and the
--           target of InvoiceItems.InvoiceID / every /employee/invoices/<id>
--           URL). InvoiceNumber is what is printed on the invoice, the PDF,
--           the History page, the success message and the PDF filename.
--
--           Existing invoices keep exactly the number they already print:
--           until now the printed number WAS InvoiceID, so the backfill
--           below copies InvoiceID into InvoiceNumber row for row. No
--           existing row is otherwise modified, and AUTO_INCREMENT is not
--           touched.
--
--           UNIQUE (uq_invoices_invoicenumber) is the hard guarantee that two
--           invoices can never share a number - see
--           services/invoice_number_service.py for the locked sequence that
--           allocates numbers (019_create_invoicenumbersequence.sql).
--
--           Re-runnable: every statement is guarded (IF NOT EXISTS / WHERE
--           InvoiceNumber IS NULL), so running it twice is harmless.
--
--           Deploy note: run 018, 019 and 020 together, then restart the
--           application immediately - the previous code does not set
--           InvoiceNumber, so it cannot create invoices once this column is
--           NOT NULL. See DEPLOYMENT.md "Invoice Number Configuration".
-- =========================================================

ALTER TABLE `Invoices`
    ADD COLUMN IF NOT EXISTS `InvoiceNumber` INT NULL AFTER `InvoiceID`;

UPDATE `Invoices`
    SET `InvoiceNumber` = `InvoiceID`
    WHERE `InvoiceNumber` IS NULL;

ALTER TABLE `Invoices`
    MODIFY COLUMN `InvoiceNumber` INT NOT NULL,
    ADD UNIQUE KEY IF NOT EXISTS `uq_invoices_invoicenumber` (`InvoiceNumber`);
