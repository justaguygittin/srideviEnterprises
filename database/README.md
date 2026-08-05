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
- Employees
- Enquiries
- ProductDetails
- ProductImages
- StockHistory
- Users

## Notes

- Catalog is the shared table with the Receipt Generator.
- Department is used for homepage category grouping.
- ProductDetails stores specifications.
- ProductImages stores image paths.
- StockHistory is employee-only. Extended in `009_alter_stockhistory_add_transaction_columns.sql` (v1.0 Sprint 5 foundation) with `TransactionType`, `QuantityChanged`, `ReferenceType`, `ReferenceID` - no new table, no rename, no existing columns/data touched.
- Users manages authentication.
