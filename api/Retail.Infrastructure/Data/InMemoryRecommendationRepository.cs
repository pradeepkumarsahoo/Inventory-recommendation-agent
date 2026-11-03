using System.Collections.Concurrent;
using Retail.Application.Abstractions;
using Retail.Domain.Entities;

namespace Retail.Infrastructure.Data;

/// <summary>
/// Thread-safe in-memory recommendation + audit store. Swap for an EF Core
/// implementation when a persistent store is needed; the interface does not
/// change, which is the point of Clean Architecture.
/// </summary>
public sealed class InMemoryRecommendationRepository : IRecommendationRepository
{
    private readonly ConcurrentDictionary<string, Recommendation> _recs = new();
    private readonly List<AuditLogEntry> _audit = new();
    private readonly object _auditLock = new();

    public Task UpsertAsync(Recommendation recommendation, CancellationToken ct = default)
    {
        _recs[recommendation.RecommendationId] = recommendation;
        return Task.CompletedTask;
    }

    public Task<Recommendation?> GetAsync(string recommendationId, CancellationToken ct = default) =>
        Task.FromResult(_recs.TryGetValue(recommendationId, out var rec) ? rec : null);

    public Task<IReadOnlyList<Recommendation>> ListAsync(string? storeId = null, CancellationToken ct = default)
    {
        IEnumerable<Recommendation> q = _recs.Values;
        if (!string.IsNullOrEmpty(storeId))
            q = q.Where(r => r.StoreId == storeId);
        return Task.FromResult<IReadOnlyList<Recommendation>>(q.ToList());
    }

    public Task AppendAuditAsync(AuditLogEntry entry, CancellationToken ct = default)
    {
        lock (_auditLock)
        {
            _audit.Add(entry);
        }
        return Task.CompletedTask;
    }

    public Task<IReadOnlyList<AuditLogEntry>> ListAuditAsync(string? recommendationId = null, CancellationToken ct = default)
    {
        lock (_auditLock)
        {
            IEnumerable<AuditLogEntry> q = _audit;
            if (!string.IsNullOrEmpty(recommendationId))
                q = q.Where(a => a.RecommendationId == recommendationId);
            return Task.FromResult<IReadOnlyList<AuditLogEntry>>(q.OrderByDescending(a => a.Timestamp).ToList());
        }
    }
}
