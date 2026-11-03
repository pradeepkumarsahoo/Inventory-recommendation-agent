using Microsoft.Extensions.Logging;
using Retail.Application.Abstractions;
using Retail.Application.Models;
using Retail.Domain.Entities;

namespace Retail.Application.Services;

public sealed class RecommendationService
{
    private readonly IAgentOrchestrator _orchestrator;
    private readonly IRecommendationRepository _repo;
    private readonly IGuardrailClient _guardrails;
    private readonly ILogger<RecommendationService> _log;

    public RecommendationService(
        IAgentOrchestrator orchestrator,
        IRecommendationRepository repo,
        IGuardrailClient guardrails,
        ILogger<RecommendationService> log)
    {
        _orchestrator = orchestrator;
        _repo = repo;
        _guardrails = guardrails;
        _log = log;
    }

    public async Task<AgentRunResult> GenerateDailyPlanAsync(string storeId, CancellationToken ct = default)
    {
        _log.LogInformation("Generating daily plan for {StoreId}", storeId);
        var run = await _orchestrator.RunDailyPlanAsync(storeId, ct);
        foreach (var rec in run.Recommendations)
        {
            await _repo.UpsertAsync(rec, ct);
        }
        return run;
    }

    public async Task<ActionExecutionResponse> ExecuteActionAsync(ActionExecutionRequest request, string actor, CancellationToken ct = default)
    {
        var rec = await _repo.GetAsync(request.RecommendationId, ct);
        if (rec is null)
            return new ActionExecutionResponse(false, "not_found", $"Recommendation {request.RecommendationId} not found.");

        var verdict = await _guardrails.AuthorizeExecutionAsync(request.RecommendationId, request.ApproverRole, ct);
        var audit = new AuditLogEntry
        {
            Actor = actor,
            ActorRole = request.ApproverRole,
            RecommendationId = request.RecommendationId,
            Decision = verdict.Allowed ? "approved" : "rejected",
            Notes = request.Notes,
            GuardrailOutcome = verdict.Reason,
        };
        await _repo.AppendAuditAsync(audit, ct);
        if (!verdict.Allowed)
        {
            _log.LogWarning("Execution blocked for {Id}: {Reason}", request.RecommendationId, verdict.Reason);
            return new ActionExecutionResponse(false, "blocked", verdict.Reason);
        }

        rec.Status = RecommendationStatus.Executed;
        await _repo.UpsertAsync(rec, ct);
        return new ActionExecutionResponse(true, rec.Status.ToString(), null);
    }
}
