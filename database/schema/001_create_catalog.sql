CREATE TABLE Catalog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(255),
    category VARCHAR(255),
    brand VARCHAR(255),
    model VARCHAR(255),
    base_price DECIMAL(10, 2),
    offer_price DECIMAL(10, 2),
    product_status VARCHAR(50),
    gst_percent DECIMAL(5, 2),
    stock_quantity INT NOT NULL DEFAULT 0
);
