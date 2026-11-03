namespace Retail.Domain.Entities;

public sealed class SalesTransaction
{
    public required string SaleId { get; init; }
    public DateOnly TransactionDate { get; init; }
    public required string StoreId { get; init; }
    public required string ProductId { get; init; }
    public int Quantity { get; init; }
    public decimal UnitPrice { get; init; }
    public decimal Revenue { get; init; }
    public decimal CostTotal { get; init; }
    public decimal GrossProfit { get; init; }
    public bool PromotionApplied { get; init; }
}
