using System.Globalization;
using CsvHelper;
using CsvHelper.Configuration;
using Microsoft.Extensions.Options;
using Retail.Application.Abstractions;
using Retail.Domain.Entities;
using Retail.Infrastructure.Options;

namespace Retail.Infrastructure.Data;

/// <summary>
/// Reads retail data from the shared /databricks/sample-data CSV directory.
/// The same contract is satisfied by DatabricksRetailDataRepository when the
/// DataSource is "databricks" (not implemented here — see data_access.py for
/// the full Databricks SQL adapter available to the Python agents).
/// </summary>
public sealed class CsvRetailDataRepository : IRetailDataRepository
{
    private readonly string _root;

    public CsvRetailDataRepository(IOptions<DataOptions> options)
    {
        _root = options.Value.SampleDataPath;
    }

    public Task<IReadOnlyList<Product>> GetProductsAsync(CancellationToken ct = default) =>
        Task.FromResult<IReadOnlyList<Product>>(ReadCsv(Path.Combine(_root, "products.csv"), r => new Product
        {
            ProductId = r["product_id"],
            Sku = r["sku"],
            Name = r["name"],
            Category = r["category"],
            Brand = r["brand"],
            Cost = decimal.Parse(r["cost"], CultureInfo.InvariantCulture),
            BasePrice = decimal.Parse(r["base_price"], CultureInfo.InvariantCulture),
            LaunchDate = DateOnly.Parse(r["launch_date"]),
            TrendingScore = double.Parse(r["trending_score"], CultureInfo.InvariantCulture),
            Seasonality = r["seasonality"],
        }));

    public Task<IReadOnlyList<Store>> GetStoresAsync(CancellationToken ct = default) =>
        Task.FromResult<IReadOnlyList<Store>>(ReadCsv(Path.Combine(_root, "stores.csv"), r => new Store
        {
            StoreId = r["store_id"],
            Name = r["name"],
            City = r["city"],
            State = r["state"],
            Lat = double.Parse(r["lat"], CultureInfo.InvariantCulture),
            Lon = double.Parse(r["lon"], CultureInfo.InvariantCulture),
            FootTrafficTier = r["foot_traffic_tier"],
        }));

    public Task<IReadOnlyList<SalesTransaction>> GetSalesAsync(string? storeId = null, CancellationToken ct = default)
    {
        var all = ReadCsv(Path.Combine(_root, "sales.csv"), r => new SalesTransaction
        {
            SaleId = r["sale_id"],
            TransactionDate = DateOnly.Parse(r["transaction_date"]),
            StoreId = r["store_id"],
            ProductId = r["product_id"],
            Quantity = int.Parse(r["quantity"], CultureInfo.InvariantCulture),
            UnitPrice = decimal.Parse(r["unit_price"], CultureInfo.InvariantCulture),
            Revenue = decimal.Parse(r["revenue"], CultureInfo.InvariantCulture),
            CostTotal = decimal.Parse(r["cost_total"], CultureInfo.InvariantCulture),
            GrossProfit = decimal.Parse(r["gross_profit"], CultureInfo.InvariantCulture),
            PromotionApplied = string.Equals(r["promotion_applied"], "True", StringComparison.OrdinalIgnoreCase),
        });
        var filtered = storeId is null ? all : all.Where(s => s.StoreId == storeId).ToList();
        return Task.FromResult<IReadOnlyList<SalesTransaction>>(filtered);
    }

    public Task<IReadOnlyList<InventorySnapshot>> GetInventoryAsync(string? storeId = null, CancellationToken ct = default)
    {
        var all = ReadCsv(Path.Combine(_root, "inventory_snapshots.csv"), r => new InventorySnapshot
        {
            StoreId = r["store_id"],
            ProductId = r["product_id"],
            SnapshotDate = DateOnly.Parse(r["snapshot_date"]),
            OnHandQuantity = int.Parse(r["on_hand_quantity"], CultureInfo.InvariantCulture),
            WeeklySalesVelocity = double.Parse(r["weekly_sales_velocity"], CultureInfo.InvariantCulture),
            ReorderPoint = int.Parse(r["reorder_point"], CultureInfo.InvariantCulture),
            AgeDays = int.Parse(r["age_days"], CultureInfo.InvariantCulture),
            LastRestockDate = DateOnly.Parse(r["last_restock_date"]),
        });
        var filtered = storeId is null ? all : all.Where(x => x.StoreId == storeId).ToList();
        return Task.FromResult<IReadOnlyList<InventorySnapshot>>(filtered);
    }

    private static List<T> ReadCsv<T>(string path, Func<IReaderRow, T> map)
    {
        using var reader = new StreamReader(path);
        using var csv = new CsvReader(reader, new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true,
            MissingFieldFound = null,
        });
        var list = new List<T>();
        csv.Read();
        csv.ReadHeader();
        while (csv.Read())
        {
            list.Add(map(csv));
        }
        return list;
    }
}
