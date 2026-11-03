using Retail.Application.Models;

namespace Retail.Application.Abstractions;

public interface IGuardrailClient
{
    Task<GuardrailVerdict> ValidateInputAsync(IDictionary<string, object> request, CancellationToken ct = default);
    Task<GuardrailVerdict> ValidateRecommendationAsync(IDictionary<string, object> recommendation, CancellationToken ct = default);
    Task<GuardrailVerdict> AuthorizeExecutionAsync(string recommendationId, string approverRole, CancellationToken ct = default);
}
