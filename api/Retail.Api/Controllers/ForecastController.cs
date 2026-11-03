using Microsoft.AspNetCore.Mvc;
using Retail.Application.Abstractions;

namespace Retail.Api.Controllers;

[ApiController]
[Route("api/forecast")]
public sealed class ForecastController : ControllerBase
{
    private readonly IRecommendationRepository _recs;
    public ForecastController(IRecommendationRepository recs) => _recs = recs;

    [HttpGet("{storeId}")]
    public async Task<IActionResult> Forecast(string storeId, CancellationToken ct)
    {
        var recs = await _recs.ListAsync(storeId, ct);
        var target = recs.FirstOrDefault(r => r.ActionType == "TARGET");
        if (target is null) return NotFound(new { error = "No forecast available. Run /api/agent/analyze first." });
        return Ok(target);
    }
}
