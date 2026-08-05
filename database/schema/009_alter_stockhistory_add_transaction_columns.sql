-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 009_alter_stockhistory_add_transaction_columns.sql
-- Purpose : v1.0 Sprint 5 foundation. Extends the existing StockHistory
--           table (created in 008_create_stockhistory.sql) with the
--           columns needed for Stock In/Stock Out/Adjustment logic.
--
--           Does NOT create a new table, does NOT rename StockHistory,
--           and does NOT modify or remove any existing column or data.
--           StockHistory remains the permanent inventory audit/history
--           table for v1.0.
--
--           Schema-drift note (v1.0 Sprint 5.1): this file originally
--           added TransactionType/QuantityChanged/ReferenceType all as
--           nullable with DEFAULT NULL. Before Sprint 5.1's write logic was
--           implemented, the live database was found to already have
--           TransactionType/QuantityChanged/ReferenceType hardened to
--           NOT NULL with defaults ('ADJUSTMENT', 0, 'MANUAL' respectively)
--           - a deliberate-looking manual change made directly against the
--           database outside of this file. Per this project's own schema
--           convention ("never manually modify schema without reflecting
--           the change back into version control" - see AI_CONTEXT.md
--           Deployment Lessons), this file was updated to match the
--           verified live schema below, rather than the drift being
--           silently reverted or ignored. See AI_CONTEXT.md for the full
--           note and how services/product_service.py's
--           apply_stock_transaction() was adapted to it.
-- =========================================================

ALTER TABLE StockHistory
    ADD COLUMN TransactionType VARCHAR(50) NOT NULL DEFAULT 'ADJUSTMENT' AFTER EmployeeID,
    ADD COLUMN QuantityChanged INT NOT NULL DEFAULT 0 AFTER NewStock,
    ADD COLUMN ReferenceType VARCHAR(50) NOT NULL DEFAULT 'MANUAL' AFTER Reason,
    ADD COLUMN ReferenceID INT DEFAULT NULL AFTER ReferenceType;

-- Indexes for the query shapes future Stock In/Stock Out screens will need:
-- history for one product, history for one employee, and history for one
-- originating reference (e.g. a future PurchaseOrder or SalesInvoice row).
ALTER TABLE StockHistory
    ADD INDEX idx_stockhistory_productid (ProductID),
    ADD INDEX idx_stockhistory_employeeid (EmployeeID),
    ADD INDEX idx_stockhistory_reference (ReferenceType, ReferenceID);

-- Foreign key to Employees only - deliberately NOT to Catalog.
--
-- Catalog is never the target of a foreign key anywhere in this schema:
-- ProductImages, ProductDetails, and Enquiries all reference Catalog.id by
-- convention only, because Catalog is the table shared with the
-- independently-deployed Receipt Generator project (see database/README.md
-- and AI_CONTEXT.md) - this project does not own that table exclusively,
-- so it does not constrain it. Adding the first-ever hard FK against
-- Catalog here would break that established, deliberate pattern.
--
-- Employees is fully internal, and Employees.UserID -> Users.UserID
-- (003_create_employees.sql) already establishes FK usage as the norm for
-- internal-only relationships, so this is a consistent extension of that
-- convention, not a new one.
--
-- ReferenceID has no foreign key: ReferenceType makes it polymorphic (which
-- table it points to depends on the value of ReferenceType), and a single
-- FK constraint cannot reference more than one target table.
ALTER TABLE StockHistory
    ADD CONSTRAINT fk_stockhistory_employeeid FOREIGN KEY (EmployeeID) REFERENCES Employees (EmployeeID);
