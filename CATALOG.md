# ============================================================
# Project : Sridevi Enterprises
# File    : CHANGELOG.md
# Purpose : Project version history
#
# Author  : Srikar
# ============================================================

# Changelog

All notable changes to this project will be documented here.

## v0.2.0

- Homepage completed
- Database architecture finalized
- MariaDB integration completed
- Blueprint routing implemented
- Project structure frozen

## v0.3.0

### Added

- Dynamic Products page
- Dynamic Product Details page
- Product Service layer
- Catalog database integration
- Department-based organization
- Search functionality
- Department filter
- Category filter
- Brand filter
- Availability filter
- Product sorting
- Responsive product grid
- Similar products section
- Placeholder image support
- Product specification support
- Product image gallery architecture

### Changed

- Replaced static products with database-driven products
- Converted application to Service Layer architecture
- Connected local MariaDB Catalog table
- Removed product prices from customer interface
- Replaced prices with "Contact for Pricing"
- Standardized product card heights
- Improved responsive layouts
- Added pagination
- Improved search performance
- Improved database query performance

### Fixed

- Partial keyword search
- Pagination bugs
- Product card alignment
- Missing image handling
- UTF-8 encoding issues
- Navigation routing issues
- Database connection issues
- Product layout inconsistencies


# v0.6.1

## Employee Products Module

Completed

- Employee Products page
- Read-only product listing
- Product search
- Department search
- Category search
- Brand search
- Pagination
- Route protection
- Session validation
- No financial information displayed
- Responsive employee table

Hotfixes

- Fixed Jinja2 pagination error by moving page calculations to Python.
- Fixed logout/session protection behavior.
- Fixed unread MySQL result issue in database helper.
