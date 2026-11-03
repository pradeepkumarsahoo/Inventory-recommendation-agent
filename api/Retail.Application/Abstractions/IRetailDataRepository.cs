using Retail.Domain.Entities;

namespace Retail.Application.Abstractions;

public interface IRetailDataRepository
{
    Task<IReadOnlyList<Product>> GetProductsAsync(CancellationToken ct = default);
    Task<IReadOnlyList<Store>> GetStoresAsync(CancellationToken ct = default);
    Task<IReadOnlyList<SalesTransaction>> GetSalesAsync(string? storeId = null, CancellationToken ct = default);
    Task<IReadOnlyList<InventorySnapshot>> GetInventoryAsync(string? storeId = null, CancellationToken ct = default);
}
