namespace Retail.Domain.Entities;

public sealed class Store
{
    public required string StoreId { get; init; }
    public required string Name { get; init; }
    public required string City { get; init; }
    public required string State { get; init; }
    public double Lat { get; init; }
    public double Lon { get; init; }
    public string FootTrafficTier { get; init; } = "medium";
}
