using FluentAssertions;
using Retail.Domain.Entities;
using Xunit;

namespace Retail.Tests.Domain;

public class InventoryBucketTests
{
    [Theory]
    [InlineData(0,   "0-30")]
    [InlineData(30,  "0-30")]
    [InlineData(45,  "31-60")]
    [InlineData(90,  "61-90")]
    [InlineData(150, "91-180")]
    [InlineData(400, "180+")]
    public void AgingBucket_IsBoundedCorrectly(int age, string expected)
    {
        var inv = new InventorySnapshot
        {
            StoreId = "S101",
            ProductId = "P001",
            SnapshotDate = new DateOnly(2026, 11, 1),
            LastRestockDate = new DateOnly(2026, 10, 1),
            AgeDays = age,
            OnHandQuantity = 10,
            ReorderPoint = 5,
            WeeklySalesVelocity = 2.5,
        };
        inv.AgingBucket.Should().Be(expected);
    }

    [Fact]
    public void StockoutRisk_WhenOnHandBelowReorderAndVelocityPositive()
    {
        var inv = new InventorySnapshot
        {
            StoreId = "S101", ProductId = "P001",
            SnapshotDate = new DateOnly(2026, 11, 1),
            LastRestockDate = new DateOnly(2026, 10, 1),
            OnHandQuantity = 3, ReorderPoint = 5, WeeklySalesVelocity = 2.0,
        };
        inv.StockoutRisk.Should().BeTrue();
    }

    [Fact]
    public void ExcessStock_WhenMoreThanTenWeeksCover()
    {
        var inv = new InventorySnapshot
        {
            StoreId = "S101", ProductId = "P001",
            SnapshotDate = new DateOnly(2026, 11, 1),
            LastRestockDate = new DateOnly(2026, 10, 1),
            OnHandQuantity = 200, ReorderPoint = 5, WeeklySalesVelocity = 2.0,
        };
        inv.ExcessStock.Should().BeTrue();
    }
}
