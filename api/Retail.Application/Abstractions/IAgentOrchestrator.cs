using Retail.Application.Models;

namespace Retail.Application.Abstractions;

public interface IAgentOrchestrator
{
    Task<AgentRunResult> RunDailyPlanAsync(string storeId, CancellationToken ct = default);
}
