using Microsoft.AspNetCore.Mvc;
using Retail.Application.Abstractions;
using Retail.Application.Services;

namespace Retail.Api.Controllers;

[ApiController]
[Route("api")]
public sealed class StoresController : ControllerBase
{
    private readonly IRetailDataRepository _repo;
    private readonly RecommendationService _service;

    public StoresController(IRetailDataRepository repo, RecommendationService service)
    {
        _repo = repo;
        _service = service;
    }

    [HttpGet("stores")]
    public async Task<IActionResult> List(CancellationToken ct) => Ok(await _repo.GetStoresAsync(ct));

    [HttpGet("store/{storeId}/daily-plan")]
    public async Task<IActionResult> DailyPlan(string storeId, CancellationToken ct)
    {
        var run = await _service.GenerateDailyPlanAsync(storeId, ct);
        return Ok(run);
    }
}
