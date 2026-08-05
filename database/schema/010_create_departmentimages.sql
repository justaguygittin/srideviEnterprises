-- =========================================================
-- Project : Sridevi Enterprises
-- File    : 010_create_departmentimages.sql
-- Purpose : Department Image Management (new feature). Stores presentation
--           information only (image, display order, active flag) for each
--           Catalog department - it is not a Departments table and does
--           not replace Catalog.Department as the source of truth for
--           product classification. DepartmentName is matched against
--           Catalog.Department by value, not by a foreign key, since
--           Catalog.Department is free text with no id of its own.
--
--           One table only, per the sprint's explicit constraint - no
--           separate Departments table, no per-department image history
--           table.
-- =========================================================

CREATE TABLE DepartmentImages (
    DepartmentID INT AUTO_INCREMENT PRIMARY KEY,
    DepartmentName VARCHAR(100) NOT NULL UNIQUE,
    ImageFilename VARCHAR(255) NOT NULL,
    DisplayOrder INT NOT NULL DEFAULT 0,
    IsActive BOOLEAN NOT NULL DEFAULT TRUE
);
