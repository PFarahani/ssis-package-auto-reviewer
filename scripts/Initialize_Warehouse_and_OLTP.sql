-- Step 1: Create the databases
CREATE DATABASE WarehouseDB;
GO

CREATE DATABASE WarehouseDB_Stage;
GO

CREATE DATABASE Northwind_OLTP;
GO

-- Step 2: Inside Northwind_OLTP, create the Customer table and insert sample data
USE Northwind_OLTP;
GO

CREATE TABLE [dbo].[Customer] (
    [CustomersIDBK] NVARCHAR(5) NOT NULL,
    [CompanyName] NVARCHAR(40) NOT NULL,
    [ContactName] NVARCHAR(30) NULL,
    [ContactTitle] NVARCHAR(30) NULL,
    [Address] NVARCHAR(60) NULL,
    [City] NVARCHAR(15) NULL,
    [Region] NVARCHAR(15) NULL,
    [PostalCode] NVARCHAR(10) NULL,
    [Country] NVARCHAR(15) NULL,
    [Phone] NVARCHAR(24) NULL,
    [Fax] NVARCHAR(24) NULL,
    CONSTRAINT [PK_Customer] PRIMARY KEY CLUSTERED ([CustomersIDBK] ASC)
    );
GO

-- Insert sample data into the Customer table
INSERT INTO [dbo].[Customer] (
    [CustomersIDBK], [CompanyName], [ContactName], [ContactTitle], [Address], [City], [Region], [PostalCode], [Country], [Phone], [Fax]
) VALUES
('ALFKI', 'Alfreds Futterkiste', 'Maria Anders', 'Sales Representative', 'Obere Str. 57', 'Berlin', NULL, '12209', 'Germany', '030-0074321', '030-0076545'),
('ANATR', 'Ana Trujillo Emparedados y helados', 'Ana Trujillo', 'Owner', 'Avda. de la Constitución 2222', 'México D.F.', NULL, '05021', 'Mexico', '(5) 555-4729', '(5) 555-3745'),
('ANTON', 'Antonio Moreno Taquería', 'Antonio Moreno', 'Owner', 'Mataderos 2312', 'México D.F.', NULL, '05023', 'Mexico', '(5) 555-3932', NULL),
('AROUT', 'Around the Horn', 'Thomas Hardy', 'Sales Representative', '120 Hanover Sq.', 'London', NULL, 'WA1 1DP', 'UK', '(171) 555-7788', '(171) 555-6750'),
('BERGS', 'Berglunds snabbköp', 'Christina Berglund', 'Order Administrator', 'Berguvsvägen 8', 'Luleå', NULL, 'S-958 22', 'Sweden', '0921-12 34 65', '0921-12 34 67');
GO

-- Step 3: Inside WarehouseDB, create a new filegroup named FGDim
USE WarehouseDB;
GO

ALTER DATABASE WarehouseDB ADD FILEGROUP FGDim;
GO

-- [Optional] add a file to the FGDim filegroup (if needed for storage)
ALTER DATABASE WarehouseDB ADD FILE (
    NAME = 'FGDim_Data',
    FILENAME = 'C:\USER\WarehouseDB_FGDim.ndf', -- Update the path as needed
    SIZE = 5MB,
    MAXSIZE = 100MB,
    FILEGROWTH = 5MB
) TO FILEGROUP FGDim;
GO