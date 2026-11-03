namespace Retail.Domain.Entities;

public sealed class Product
{
    public required string ProductId { get; init; }
    public required string Sku { get; init; }
    public required string Name { get; init; }
    public required string Category { get; init; }
    public required string Brand { get; init; }
    public decimal Cost { get; init; }
    public decimal BasePrice { get; init; }
    public DateOnly LaunchDate { get; init; }
    public double TrendingScore { get; init; }
    public string Seasonality { get; init; } = "none";

    public decimal GrossMarginPercent =>
        BasePrice == 0 ? 0 : Math.Round(((BasePrice - Cost) / BasePrice) * 100m, 2);
}
