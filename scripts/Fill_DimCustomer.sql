/*
Table Name: DimCustomers
Created Date: 2025-01-07
Created By: PFarahani
*/

---------------------------------------------------------------------------
--Create Table DimCustomers
USE
    WarehouseDB
GO
DROP TABLE IF EXISTS DimCustomers
GO
CREATE TABLE DimCustomers
(
    CustomersKey  INT PRIMARY KEY NONCLUSTERED WITH (DATA_COMPRESSION = PAGE),
    CustomersIDBK INT,
    CompanyName   NVARCHAR(40),
    ContactName   NVARCHAR(30),
    ContactTitle  NVARCHAR(30),
    Address       NVARCHAR(60),
    City          NVARCHAR(15),
    Region        NVARCHAR(15),
    PostalCode    NVARCHAR(10),
    Country       NVARCHAR(15),
    Phone         NVARCHAR(24),
    Fax           NVARCHAR(24),
    HashRecord    VARBINARY(500),
    ETLTime       DATETIME
) ON FGDim
  WITH (DATA_COMPRESSION = PAGE)
GO
CREATE
    CLUSTERED INDEX IX_Clustered ON DimCustomers (CustomersIDBK) WITH (DATA_COMPRESSION = PAGE) ON FGDim
GO

---------------------------------------------------------------------------
--Stage Initialization
USE WarehouseDB_Stage
GO
DROP TABLE IF EXISTS DimCustomersStage
GO
CREATE TABLE DimCustomersStage
(
    CustomersIDBK INT,
    CompanyName   NVARCHAR(40),
    ContactName   NVARCHAR(30),
    ContactTitle  NVARCHAR(30),
    Address       NVARCHAR(60),
    City          NVARCHAR(15),
    Region        NVARCHAR(15),
    PostalCode    NVARCHAR(10),
    Country       NVARCHAR(15),
    Phone         NVARCHAR(24),
    Fax           NVARCHAR(24),
    HashRecord    VARBINARY(500),
    IsExists      BIT
);
GO

---------------------------------------------------------------------------
--Get Record from OLTP
SELECT CustomersIDBK,
       CompanyName,
       ContactName,
       ContactTitle,
       Address,
       City,
       Region,
       PostalCode,
       Country,
       Phone,
       Fax
FROM Customer;

---------------------------------------------------------------------------
--Create Clustered Index on Stage Table
CREATE CLUSTERED INDEX IX_Clustered ON DimCustomersStage (CustomersIDBK)
    WITH (DATA_COMPRESSION = PAGE)
GO

---------------------------------------------------------------------------
--Update IsExists
USE WarehouseDB_Stage
GO
UPDATE DimCustomersStage
SET IsExists = 1
FROM DimCustomersStage
         INNER JOIN WarehouseDB..DimCustomers ON
    DimCustomersStage.CustomersIDBK = DimCustomers.CustomersIDBK
GO

---------------------------------------------------------------------------
--Get Data from Stage
USE WarehouseDB_Stage
GO
SELECT CustomersIDBK AS CustomersKey,
       CustomersIDBK,
       CompanyName,
       ContactName,
       ContactTitle,
       Address,
       City,
       Region,
       PostalCode,
       Country,
       Phone,
       Fax,
       HashRecord,
       GETDATE()     AS ETLTime
FROM DimCustomersStage
WHERE IsExists IS NULL
GO

---------------------------------------------------------------------------
--Update DW Table
USE WarehouseDB
GO
UPDATE DimCustomers
SET CompanyName  = DimCustomersStage.CompanyName,
    ContactName  = DimCustomersStage.ContactName,
    ContactTitle = DimCustomersStage.ContactTitle,
    Address      = DimCustomersStage.Address,
    City         = DimCustomersStage.City,
    Region       = DimCustomersStage.Region,
    PostalCode   = DimCustomersStage.PostalCode,
    Country      = DimCustomersStage.Country,
    Phone        = DimCustomersStage.Phone,
    Fax          = DimCustomersStage.Fax,
    HashRecord   = DimCustomersStage.HashRecord,
    ETLTime      = GETDATE()
FROM DimCustomers
         INNER JOIN WarehouseDB_Stage..DimCustomersStage ON
    DimCustomers.CustomersIDBK =
    DimCustomersStage.CustomersIDBK
        AND DimCustomersStage.IsExists = 1
        AND DimCustomers.HashRecord <> DimCustomersStage.HashRecord
GO

---------------------------------------------------------------------------
--Insert PackageLog
USE WarehouseDB
GO
EXEC usp_PackageExecuteLog_Insert 'DimCustomers', ?, ?
GO