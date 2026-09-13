-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 014_create_invoiceitems.sql
-- Purpose : InvoiceItems - one row per line item on an Invoice
--           (013_create_invoices.sql). See AI_CONTEXT.md "Invoice
--           Generator Module (Merge)".
--
--           ProductName, Model, HSN, UnitPrice, and GSTPercent are a
--           SNAPSHOT of the Catalog product at the moment the invoice was
--           generated - services/invoice_service.py writes them once and
--           never re-derives them from Catalog. If a product's price,
--           model, or GST rate is edited later, every previously generated
--           invoice must keep showing exactly what was charged at the
--           time - it is never recalculated from the current Catalog row.
-- =========================================================

CREATE TABLE `InvoiceItems` (
    `ItemID` INT AUTO_INCREMENT PRIMARY KEY,
    `InvoiceID` INT NOT NULL,

    -- Catalog is fully internal to this application after the Receipt
    -- Generator merge (no second, independently-deployed project writes to
    -- it any more), so - unlike every pre-existing table in this schema
    -- (ProductImages, ProductDetails, StockHistory, Enquiries), which
    -- deliberately reference Catalog.id WITHOUT a foreign key because
    -- Catalog used to be shared with that external project - InvoiceItems
    -- is free to add Catalog's first real inbound FK. See
    -- database/README.md for the full history of that convention.
    `ProductID` INT NOT NULL,

    `ProductName` VARCHAR(255) NOT NULL,
    `Model` VARCHAR(255),
    `HSN` VARCHAR(20) NOT NULL,
    `Quantity` INT NOT NULL,
    `UnitPrice` DECIMAL(10, 2) NOT NULL,
    `GSTPercent` DECIMAL(5, 2) NOT NULL,
    `TaxableValue` DECIMAL(12, 2) NOT NULL,
    `CGSTAmount` DECIMAL(12, 2) NOT NULL DEFAULT 0,
    `SGSTAmount` DECIMAL(12, 2) NOT NULL DEFAULT 0,
    `IGSTAmount` DECIMAL(12, 2) NOT NULL DEFAULT 0,
    `LineTotal` DECIMAL(12, 2) NOT NULL,

    CONSTRAINT `fk_invoiceitems_invoiceid` FOREIGN KEY (`InvoiceID`) REFERENCES `Invoices` (`InvoiceID`),
    CONSTRAINT `fk_invoiceitems_productid` FOREIGN KEY (`ProductID`) REFERENCES `Catalog` (`id`),

    INDEX `idx_invoiceitems_invoiceid` (`InvoiceID`),
    INDEX `idx_invoiceitems_productid` (`ProductID`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
