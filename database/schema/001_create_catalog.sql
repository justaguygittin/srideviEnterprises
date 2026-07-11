-- gsrikari_sridevi_enterprises.`catalog` definition

CREATE TABLE `catalog` (
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
