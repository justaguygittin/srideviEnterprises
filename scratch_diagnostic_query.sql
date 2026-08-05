-- TEMPORARY diagnostic query - run in phpMyAdmin's SQL tab against production.
-- Not part of the app; delete this file once the investigation is done.

-- Full picture: every distinct Department string in Catalog, with byte length
-- vs character length (a mismatch means multi-byte UTF-8, e.g. a non-breaking
-- space U+00A0 or a smart quote), plus the raw hex bytes and how many Catalog
-- rows use that exact string.
SELECT
    CONCAT('[', Department, ']') AS Bracketed,
    LENGTH(Department)           AS ByteLength,
    CHAR_LENGTH(Department)      AS CharLength,
    HEX(Department)              AS HexValue,
    COUNT(*)                     AS RowCount
FROM Catalog
GROUP BY Department
ORDER BY Department;

-- Narrowed to the department in question, in case the full list above is too
-- long to scan by eye. LIKE deliberately avoids '&' since a mismatched
-- surrounding-whitespace or lookalike character could sit right next to it.
SELECT
    CONCAT('[', Department, ']') AS Bracketed,
    LENGTH(Department)           AS ByteLength,
    CHAR_LENGTH(Department)      AS CharLength,
    HEX(Department)              AS HexValue,
    COUNT(*)                     AS RowCount
FROM Catalog
WHERE Department LIKE '%Computer%'
GROUP BY Department
ORDER BY Department;
