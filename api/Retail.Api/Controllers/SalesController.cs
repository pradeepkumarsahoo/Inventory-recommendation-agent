using Microsoft.AspNetCore.Mvc;
using Retail.Application.Abstractions;

namespace Retail.Api.Controllers;

[ApiController]
[Route("api/sales")]
public sealed class SalesController : ControllerBase
{
    private readonly IRetailDataRepository _repo;
    public SalesController(IRetailDataRepository repo) => _repo = repo;

    [HttpGet("summary")]
    public async Task<IActionResult> Summary([FromQuery] string? storeId, CancellationToken ct)
    {
        var sales = await _repo.GetSalesAsync(storeId, ct);
        var grouped = sales
            .GroupBy(s => new { s.StoreId, s.ProductId })
            .Select(g => new
            {
                g.Key.StoreId,
                g.Key.ProductId,
                UnitsSold = g.Sum(x => x.Quantity),
                Revenue = g.Sum(x => x.Revenue),
                GrossProfit = g.Sum(x => x.GrossProfit),
                Transactions = g.Count(),
                WeeklyVelocity = Math.Round(g.Sum(x => x.Quantity) / 13.0, 2),
            });
        return Ok(grouped);
    }
}
