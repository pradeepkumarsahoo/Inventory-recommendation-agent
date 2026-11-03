using Retail.Domain.Entities;

namespace Retail.Application.Models;

public sealed record AgentRunResult(
    string StoreId,
    DateTimeOffset GeneratedAt,
    IReadOnlyList<Recommendation> Recommendations,
    IReadOnlyList<AgentTraceStep> Trace,
    IReadOnlyDictionary<string, object> Insights);

public sealed record AgentTraceStep(string Agent, string Step, string Detail);

public sealed record GuardrailVerdict(bool Allowed, string? Reason);

public sealed record ActionExecutionRequest(string RecommendationId, string ApproverRole, string? Notes = null);

public sealed record ActionExecutionResponse(bool Executed, string Status, string? Reason);
