namespace Retail.Domain.Entities;

public enum RecommendationStatus
{
    Pending,
    Approved,
    Rejected,
    Executed,
    Expired,
}

public sealed class Recommendation
{
    public required string RecommendationId { get; init; }
    public required string StoreId { get; init; }
    public string? ProductId { get; init; }
    public string? DestinationStoreId { get; init; }
    public required string ActionType { get; init; }
    public required string Title { get; init; }
    public required string Justification { get; init; }
    public IReadOnlyDictionary<string, object> SupportingMetrics { get; init; } =
        new Dictionary<string, object>();
    public decimal ExpectedSalesImpact { get; init; }
    public decimal ExpectedMarginImpact { get; init; }
    public double Confidence { get; init; }
    public required string Priority { get; init; }
    public IReadOnlyList<string> Risks { get; init; } = Array.Empty<string>();
    public IReadOnlyList<string> Assumptions { get; init; } = Array.Empty<string>();
    public required string RequiredApproval { get; init; }
    public required string ResponsibleRole { get; init; }
    public int DeadlineHours { get; init; }
    public required string SuccessKpi { get; init; }
    public required string SourceAgent { get; init; }
    public DateTimeOffset CreatedAt { get; init; }
    public RecommendationStatus Status { get; set; } = RecommendationStatus.Pending;
}
