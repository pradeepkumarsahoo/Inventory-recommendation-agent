using Microsoft.AspNetCore.Mvc;
using Retail.Application.Abstractions;

namespace Retail.Api.Controllers;

[ApiController]
[Route("api/inventory")]
public sealed class InventoryController : ControllerBase
{
    private readonly IRetailDataRepository _repo;
    private readonly IRecommendationRepository _recs;
    public InventoryController(IRetailDataRepository repo, IRecommendationRepository recs)
    { _repo = repo; _recs = recs; }

    [HttpGet("aging")]
    public async Task<IActionResult> Aging([FromQuery] string? storeId, CancellationToken ct)
    {
        var inv = await _repo.GetInventoryAsync(storeId, ct);
        var buckets = inv.GroupBy(i => i.AgingBucket)
            .ToDictionary(g => g.Key, g => new
            {
                units = g.Sum(x => x.OnHandQuantity),
                lines = g.Count(),
            });
        return Ok(buckets);
    }

    [HttpGet("recommendations")]
    public async Task<IActionResult> Recommendations([FromQuery] string? storeId, CancellationToken ct)
    {
        var recs = await _recs.ListAsync(storeId, ct);
        return Ok(recs.Where(r => r.ActionType is "TRANSFER" or "REPLENISH" or "MARKDOWN" or "CLEARANCE" or "BUNDLE" or "PROMOTE"));
    }
}
