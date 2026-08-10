# Database Documentation

## Database

MariaDB

## Development Configuration

Host: 127.0.0.1

Port: 3307

Database:
gsrikari_Sridevi_Enterprises

## Tables

- Catalog
- Customers
- DepartmentImages
- Employees
- Enquiries
- ProductDetails
- ProductImages
- StockHistory
- Users

## Schema Files

The canonical schema is `database/schema/`, files `001_create_catalog.sql` through
`011_alter_catalog_add_soft_delete.sql`. Create any new database by importing **all**
of them in numeric order — see DEPLOYMENT.md § 1.4, which lists what each file does.
Never create a database from an export or a partial import.

## Notes

- Catalog is the shared table with the Receipt Generator.
- Catalog gained `IsActive`, `DeletedAt`, and `DeletedBy` in
  `011_alter_catalog_add_soft_delete.sql` (v1.0 Sprint 7, Product Lifecycle
  Management). Products are soft-deleted (deactivated) by setting `IsActive = 0` -
  there is no hard `DELETE` anywhere in this codebase. `IsActive` defaults to `TRUE`,
  so existing rows, and any row the Receipt Generator inserts, stay visible by default.
- Department is used for homepage category grouping.
- DepartmentImages (`010_create_departmentimages.sql`, Department Image Management) stores presentation-only data (image filename, display order, active flag) for each Catalog department, matched by `DepartmentName` (UNIQUE). It is not a Departments table and does not replace `Catalog.Department` as the source of truth for product classification - a department only needs a Catalog row, never the other way around.
- ProductDetails stores specifications.
- ProductImages stores image paths.
- StockHistory is employee-only. Extended in `009_alter_stockhistory_add_transaction_columns.sql` (v1.0 Sprint 5 foundation) with `TransactionType`, `QuantityChanged`, `ReferenceType`, `ReferenceID` - no new table, no rename, no existing columns/data touched.
- Users manages authentication.
