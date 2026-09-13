-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 012_add_performance_indexes.sql
-- Purpose : v1.1 Sprint 12 (Production Stabilization). Adds indexes for
--           the query shapes already in production use - the Products
--           page/filter sidebar (Department, category, brand) and every
--           product-detail lookup (ProductImages/ProductDetails by
--           ProductID) - none of which had anything beyond a primary key
--           before this file. See RELEASE_NOTES.md "Minimal indexing"
--           and AI_CONTEXT.md "v1.1 - Deferred From v1.0.0".
--
--           Does NOT create a table, does NOT alter any column, does NOT
--           change any data. Purely additive indexes - safe to run
--           against a live database with existing rows, and safe to run
--           as part of a fresh install.
-- =========================================================

ALTER TABLE `Catalog`
    ADD INDEX idx_catalog_department (`Department`),
    ADD INDEX idx_catalog_category (`category`),
    ADD INDEX idx_catalog_brand (`brand`);

ALTER TABLE ProductImages
    ADD INDEX idx_productimages_productid (ProductID);

ALTER TABLE ProductDetails
    ADD INDEX idx_productdetails_productid (ProductID);
