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

## Notes

- Catalog is the shared table with the Receipt Generator.
- Department is used for homepage category grouping.
- DepartmentImages (`010_create_departmentimages.sql`, Department Image Management) stores presentation-only data (image filename, display order, active flag) for each Catalog department, matched by `DepartmentName` (UNIQUE). It is not a Departments table and does not replace `Catalog.Department` as the source of truth for product classification - a department only needs a Catalog row, never the other way around.
- ProductDetails stores specifications.
- ProductImages stores image paths.
- StockHistory is employee-only. Extended in `009_alter_stockhistory_add_transaction_columns.sql` (v1.0 Sprint 5 foundation) with `TransactionType`, `QuantityChanged`, `ReferenceType`, `ReferenceID` - no new table, no rename, no existing columns/data touched.
- Users manages authentication.
