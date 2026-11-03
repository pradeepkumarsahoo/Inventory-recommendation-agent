namespace Retail.Domain.Entities;

public sealed class InventorySnapshot
{
    public required string StoreId { get; init; }
    public required string ProductId { get; init; }
    public DateOnly SnapshotDate { get; init; }
    public int OnHandQuantity { get; init; }
    public double WeeklySalesVelocity { get; init; }
    public int ReorderPoint { get; init; }
    public int AgeDays { get; init; }
    public DateOnly LastRestockDate { get; init; }

    public string AgingBucket => AgeDays switch
    {
        <= 30  => "0-30",
        <= 60  => "31-60",
        <= 90  => "61-90",
        <= 180 => "91-180",
        _      => "180+",
    };

    public double WeeksOfCover =>
        WeeklySalesVelocity <= 0 ? double.PositiveInfinity : OnHandQuantity / WeeklySalesVelocity;

    public bool StockoutRisk => WeeklySalesVelocity > 0 && OnHandQuantity < ReorderPoint;
    public bool ExcessStock  => WeeklySalesVelocity > 0 && WeeksOfCover > 10;
}
