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
- InvoiceItems
- Invoices
- ProductDetails
- ProductImages
- StockHistory
- Users

## Schema Files

The canonical schema is `database/schema/`, files `001_create_catalog.sql` through
`014_create_invoiceitems.sql`. Create any new database by importing **all**
of them in numeric order — see DEPLOYMENT.md § 1.4, which lists what each file does.
Never create a database from an export or a partial import.

## Notes

- Catalog was historically the shared table with the Receipt Generator - see
  the Invoice Generator Module (Merge) note below; that project has since
  been folded into this application, so Catalog is now fully internal.
- Invoices / InvoiceItems (`013_create_invoices.sql`, `014_create_invoiceitems.sql`
  — Invoice Generator Module merge, see AI_CONTEXT.md) store every generated
  GST invoice. InvoiceItems snapshots each line's product name/model/HSN/
  price/GST% at generation time and is never re-derived from Catalog later.
  `InvoiceItems.ProductID` is Catalog's first real inbound foreign key -
  every other table below deliberately has none, because Catalog used to be
  shared with the independently-deployed Receipt Generator project; that
  reason no longer applies now that Catalog is fully internal.
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
- `012_add_performance_indexes.sql` (v1.1 Sprint 12) adds indexes on `Catalog.Department`/`category`/`brand` and `ProductImages`/`ProductDetails.ProductID` - purely additive, no column/table change.
