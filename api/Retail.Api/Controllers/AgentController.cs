using Microsoft.AspNetCore.Mvc;
using Retail.Application.Abstractions;
using Retail.Application.Models;
using Retail.Application.Services;

namespace Retail.Api.Controllers;

[ApiController]
[Route("api/agent")]
public sealed class AgentController : ControllerBase
{
    private readonly RecommendationService _service;
    private readonly IRecommendationRepository _recs;

    public AgentController(RecommendationService service, IRecommendationRepository recs)
    {
        _service = service;
        _recs = recs;
    }

    public sealed record AnalyzeRequest(string StoreId);

    [HttpPost("analyze")]
    public async Task<IActionResult> Analyze([FromBody] AnalyzeRequest req, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(req.StoreId))
            return BadRequest(new { error = "StoreId is required." });
        var result = await _service.GenerateDailyPlanAsync(req.StoreId, ct);
        return Ok(result);
    }

    [HttpGet("decisions")]
    public async Task<IActionResult> Decisions([FromQuery] string? storeId, CancellationToken ct) =>
        Ok(await _recs.ListAsync(storeId, ct));

    [HttpGet("audit")]
    public async Task<IActionResult> Audit([FromQuery] string? recommendationId, CancellationToken ct) =>
        Ok(await _recs.ListAuditAsync(recommendationId, ct));

    [HttpPost("execute-action")]
    public async Task<IActionResult> Execute([FromBody] ActionExecutionRequest req, CancellationToken ct)
    {
        var actor = User.Identity?.Name ?? "anonymous";
        var result = await _service.ExecuteActionAsync(req, actor, ct);
        return result.Executed ? Ok(result) : StatusCode(StatusCodes.Status409Conflict, result);
    }
}
