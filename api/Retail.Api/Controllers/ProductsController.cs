using Microsoft.AspNetCore.Mvc;
using Retail.Application.Abstractions;

namespace Retail.Api.Controllers;

[ApiController]
[Route("api/products")]
public sealed class ProductsController : ControllerBase
{
    private readonly IRetailDataRepository _repo;
    public ProductsController(IRetailDataRepository repo) => _repo = repo;

    [HttpGet]
    public async Task<IActionResult> List(CancellationToken ct)
    {
        var products = await _repo.GetProductsAsync(ct);
        return Ok(products);
    }

    [HttpGet("trending")]
    public async Task<IActionResult> Trending(CancellationToken ct)
    {
        var products = await _repo.GetProductsAsync(ct);
        var top = products.OrderByDescending(p => p.TrendingScore).Take(10)
            .Select(p => new { p.ProductId, p.Name, p.Category, p.TrendingScore, p.GrossMarginPercent });
        return Ok(top);
    }
}
