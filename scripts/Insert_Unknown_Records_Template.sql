USE [YourDatabaseName]
GO

-- Template for inserting null/unknown records into dimension tables
-- These records typically use a negative key value (-100) and represent "No Value" or "Unknown" entries

-- FINANCIAL DIMENSIONS
INSERT INTO DimTable1(Table1Key, Table1IDBK, Table1Name, Table1Category, Table1Type)
VALUES(-100, -100, N'No BI Value', N'No BI Value', N'No BI Value')

INSERT INTO DimTable2(Table2Key, Table2IDBK, Table2Name, Table2Attribute1, Table2Attribute2)
VALUES(-100, -100, N'No BI Value', N'No BI Value', N'No BI Value')

-- COMMON DIMENSIONS
INSERT INTO DimTable3(Table3Key, Table3IDBK, Table3Name, Table3Description)
VALUES(-100, -100, N'No BI Value', N'No BI Value')

INSERT INTO DimTable4(Table4Key, Table4IDBK, Table4Name)
VALUES(-100, -100, N'No BI Value')
