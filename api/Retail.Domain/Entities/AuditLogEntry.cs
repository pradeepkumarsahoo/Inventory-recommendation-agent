namespace Retail.Domain.Entities;

public sealed class AuditLogEntry
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public DateTimeOffset Timestamp { get; init; } = DateTimeOffset.UtcNow;
    public required string Actor { get; init; }
    public required string ActorRole { get; init; }
    public required string RecommendationId { get; init; }
    public required string Decision { get; init; }      // approved | rejected | executed
    public string? Notes { get; init; }
    public string? GuardrailOutcome { get; init; }
}
