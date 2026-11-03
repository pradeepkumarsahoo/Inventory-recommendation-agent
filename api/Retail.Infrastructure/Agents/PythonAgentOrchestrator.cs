using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Retail.Application.Abstractions;
using Retail.Application.Models;
using Retail.Domain.Entities;
using Retail.Infrastructure.Options;

namespace Retail.Infrastructure.Agents;

/// <summary>
/// Bridges to the Python agent system by invoking the supervisor as a
/// subprocess and parsing its JSON output. In a production deployment, the
/// Python agents would be a long-running sidecar reached over gRPC/HTTP; the
/// subprocess bridge keeps local development dependency-free.
/// </summary>
public sealed class PythonAgentOrchestrator : IAgentOrchestrator
{
    private readonly AgentOptions _opts;
    private readonly ILogger<PythonAgentOrchestrator> _log;

    public PythonAgentOrchestrator(IOptions<AgentOptions> opts, ILogger<PythonAgentOrchestrator> log)
    {
        _opts = opts.Value;
        _log = log;
    }

    public async Task<AgentRunResult> RunDailyPlanAsync(string storeId, CancellationToken ct = default)
    {
        var psi = new ProcessStartInfo
        {
            FileName = _opts.PythonExecutable,
            WorkingDirectory = _opts.AgentRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add("-m");
        psi.ArgumentList.Add("retail_agents.supervisor");
        psi.ArgumentList.Add(storeId);
        psi.EnvironmentVariables["PYTHONPATH"] = ".";

        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException("Failed to launch Python agent process.");

        var stdout = new StringBuilder();
        var stderr = new StringBuilder();
        proc.OutputDataReceived += (_, e) => { if (e.Data is not null) stdout.AppendLine(e.Data); };
        proc.ErrorDataReceived  += (_, e) => { if (e.Data is not null) stderr.AppendLine(e.Data); };
        proc.BeginOutputReadLine();
        proc.BeginErrorReadLine();

        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(TimeSpan.FromSeconds(_opts.TimeoutSeconds));
        await proc.WaitForExitAsync(cts.Token).ConfigureAwait(false);

        if (proc.ExitCode != 0)
        {
            _log.LogError("Python agent exited {Code}: {Err}", proc.ExitCode, stderr.ToString());
            throw new InvalidOperationException($"Agent run failed with exit code {proc.ExitCode}.");
        }

        var json = stdout.ToString();
        return Parse(json);
    }

    private static AgentRunResult Parse(string json)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;
        var storeId = root.GetProperty("store_id").GetString()!;
        var generatedAt = DateTimeOffset.Parse(root.GetProperty("generated_at").GetString()!);
        var recs = new List<Recommendation>();
        foreach (var r in root.GetProperty("recommendations").EnumerateArray())
        {
            recs.Add(ParseRecommendation(r));
        }
        var trace = new List<AgentTraceStep>();
        foreach (var t in root.GetProperty("agent_trace").EnumerateArray())
        {
            trace.Add(new AgentTraceStep(
                t.GetProperty("agent").GetString()!,
                t.GetProperty("step").GetString()!,
                t.GetProperty("detail").ToString()));
        }
        var insights = new Dictionary<string, object>();
        foreach (var p in root.GetProperty("insights").EnumerateObject())
        {
            insights[p.Name] = p.Value.Clone();
        }
        return new AgentRunResult(storeId, generatedAt, recs, trace, insights);
    }

    private static Recommendation ParseRecommendation(JsonElement e)
    {
        var metrics = new Dictionary<string, object>();
        foreach (var m in e.GetProperty("supporting_metrics").EnumerateObject())
            metrics[m.Name] = m.Value.Clone();

        return new Recommendation
        {
            RecommendationId = e.GetProperty("recommendation_id").GetString()!,
            StoreId = e.GetProperty("store_id").GetString()!,
            ProductId = e.TryGetProperty("product_id", out var pid) && pid.ValueKind == JsonValueKind.String ? pid.GetString() : null,
            DestinationStoreId = e.TryGetProperty("destination_store_id", out var d) && d.ValueKind == JsonValueKind.String ? d.GetString() : null,
            ActionType = e.GetProperty("action_type").GetString()!,
            Title = e.GetProperty("title").GetString()!,
            Justification = e.GetProperty("justification").GetString()!,
            SupportingMetrics = metrics,
            ExpectedSalesImpact = e.GetProperty("expected_sales_impact").GetDecimal(),
            ExpectedMarginImpact = e.GetProperty("expected_margin_impact").GetDecimal(),
            Confidence = e.GetProperty("confidence").GetDouble(),
            Priority = e.GetProperty("priority").GetString()!,
            Risks = e.GetProperty("risks").EnumerateArray().Select(x => x.GetString()!).ToList(),
            Assumptions = e.GetProperty("assumptions").EnumerateArray().Select(x => x.GetString()!).ToList(),
            RequiredApproval = e.GetProperty("required_approval").GetString()!,
            ResponsibleRole = e.GetProperty("responsible_role").GetString()!,
            DeadlineHours = e.GetProperty("deadline_hours").GetInt32(),
            SuccessKpi = e.GetProperty("success_kpi").GetString()!,
            SourceAgent = e.GetProperty("source_agent").GetString()!,
            CreatedAt = DateTimeOffset.Parse(e.GetProperty("created_at").GetString()!),
        };
    }
}
