-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 001_create_catalog.sql
-- Purpose : Catalog - the product table. Shared with the independently
--           deployed Receipt Generator project, which is why nothing in
--           this schema ever declares a foreign key against it (see
--           database/README.md and 009/011 for that convention).
--
--           Table name casing (v1.0 Sprint 11): this file originally read
--           CREATE TABLE `catalog`, all lowercase, while every other file
--           in this directory uses PascalCase and every query in the
--           application says `Catalog`. That mismatch is invisible on
--           Windows/macOS, where MariaDB defaults to
--           lower_case_table_names=1 and folds all table names to
--           lowercase - which is why it survived this long. On Linux, the
--           deployment target, the default is lower_case_table_names=0 and
--           table names ARE case-sensitive: a fresh install would create
--           `catalog` and then fail with "Table '...Catalog' doesn't
--           exist" on essentially every page. Renamed to `Catalog` to match
--           the application and the rest of this directory.
--
--           This affects newly created databases only - no existing
--           deployment re-runs this file.
-- =========================================================

CREATE TABLE `Catalog` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `product_id` varchar(50) DEFAULT NULL,
    `product_name` varchar(255) DEFAULT NULL,
    `Department` varchar(100) DEFAULT NULL,
    `category` varchar(255) DEFAULT NULL,
    `brand` varchar(255) DEFAULT NULL,
    `model` varchar(255) DEFAULT NULL,
    `base_price` decimal(10, 2) DEFAULT NULL,
    `offer_price` decimal(10, 2) DEFAULT NULL,
    `product_status` varchar(50) DEFAULT NULL,
    `gst_percent` decimal(5, 2) DEFAULT NULL,
    `stock_quantity` int(11) DEFAULT 0,
    PRIMARY KEY (`id`)
) ENGINE = InnoDB AUTO_INCREMENT = 314 DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_uca1400_ai_ci;
