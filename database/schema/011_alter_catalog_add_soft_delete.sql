-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 011_alter_catalog_add_soft_delete.sql
-- Purpose : v1.0 Sprint 7 (Product Lifecycle Management). Extends the
--           existing Catalog table (001_create_catalog.sql) with the
--           columns needed to soft-delete products instead of hard
--           deleting them.
--
--           Does NOT create a new table (e.g. no ProductArchive), does
--           NOT rename Catalog, and does NOT modify or remove any
--           existing column or data. This replaces delete_product()'s
--           previous hard DELETE with a deactivate/restore flow - see
--           AI_CONTEXT.md "Product Deletion" and "Soft Delete Product"
--           (Planned Roadmap) for the full history of this decision.
-- =========================================================

ALTER TABLE Catalog
    ADD COLUMN IsActive BOOLEAN NOT NULL DEFAULT TRUE AFTER stock_quantity,
    ADD COLUMN DeletedAt DATETIME NULL DEFAULT NULL AFTER IsActive,
    ADD COLUMN DeletedBy INT NULL DEFAULT NULL AFTER DeletedAt;

-- IsActive defaults TRUE so every existing catalog row (and any row the
-- independently-deployed Receipt Generator project inserts into this
-- shared table in the future) stays visible everywhere by default - no
-- backfill needed, nothing needs to be explicitly "activated".

-- No foreign key on DeletedBy, deliberately. Catalog is shared with the
-- independently-deployed Receipt Generator project (see database/README.md
-- and AI_CONTEXT.md) - this project does not own that table exclusively,
-- so its own schema/constraint surface is kept as small as possible.
-- DeletedBy conceptually references Employees.EmployeeID (the same id
-- StockHistory.EmployeeID uses, resolved via
-- services/auth_service.py:get_employee_id_for_user()), but that link is
-- enforced in the service layer (services/product_service.py:
-- deactivate_product()), not with a database constraint - consistent with
-- StockHistory.ProductID's existing "no FK to/from Catalog" convention.
