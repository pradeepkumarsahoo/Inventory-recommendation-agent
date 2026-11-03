using Retail.Domain.Entities;

namespace Retail.Application.Abstractions;

public interface IRecommendationRepository
{
    Task UpsertAsync(Recommendation recommendation, CancellationToken ct = default);
    Task<Recommendation?> GetAsync(string recommendationId, CancellationToken ct = default);
    Task<IReadOnlyList<Recommendation>> ListAsync(string? storeId = null, CancellationToken ct = default);
    Task AppendAuditAsync(AuditLogEntry entry, CancellationToken ct = default);
    Task<IReadOnlyList<AuditLogEntry>> ListAuditAsync(string? recommendationId = null, CancellationToken ct = default);
}
