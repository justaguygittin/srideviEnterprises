CREATE TABLE StockHistory (
    HistoryID INT AUTO_INCREMENT PRIMARY KEY,
    ProductID INT NOT NULL,
    EmployeeID INT NOT NULL,
    OldStock INT,
    NewStock INT,
    Reason TEXT,
    UpdateDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
