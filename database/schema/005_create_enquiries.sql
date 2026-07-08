CREATE TABLE Enquiries (
    EnquiryID INT AUTO_INCREMENT PRIMARY KEY,
    ProductID INT NULL,
    CustomerName VARCHAR(100),
    Phone VARCHAR(20),
    Email VARCHAR(100),
    Message TEXT,
    Status VARCHAR(20) DEFAULT 'Pending',
    EnquiryDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
