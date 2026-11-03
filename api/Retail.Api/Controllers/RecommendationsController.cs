using Microsoft.AspNetCore.Mvc;
using Retail.Application.Abstractions;

namespace Retail.Api.Controllers;

[ApiController]
[Route("api/recommendations")]
public sealed class RecommendationsController : ControllerBase
{
    private readonly IRecommendationRepository _recs;
    public RecommendationsController(IRecommendationRepository recs) => _recs = recs;

    [HttpGet("front-office")]
    public async Task<IActionResult> FrontOffice([FromQuery] string? storeId, CancellationToken ct) =>
        Ok((await _recs.ListAsync(storeId, ct)).Where(r => r.ActionType == "FRONT_OFFICE"));

    [HttpGet("transfers")]
    public async Task<IActionResult> Transfers([FromQuery] string? storeId, CancellationToken ct) =>
        Ok((await _recs.ListAsync(storeId, ct)).Where(r => r.ActionType == "TRANSFER"));

    [HttpGet]
    public async Task<IActionResult> List([FromQuery] string? storeId, CancellationToken ct) =>
        Ok(await _recs.ListAsync(storeId, ct));
}

[ApiController]
[Route("api/pricing")]
public sealed class PricingController : ControllerBase
{
    private readonly IRecommendationRepository _recs;
    public PricingController(IRecommendationRepository recs) => _recs = recs;

    [HttpGet("optimization")]
    public async Task<IActionResult> Optimization([FromQuery] string? storeId, CancellationToken ct) =>
        Ok((await _recs.ListAsync(storeId, ct)).Where(r => r.ActionType == "PRICING"));
}
