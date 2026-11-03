using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Retail.Application.Abstractions;
using Retail.Application.Models;
using Retail.Infrastructure.Options;

namespace Retail.Infrastructure.Guardrails;

/// <summary>
/// Calls the Python guardrail service via a short-lived subprocess. The
/// service enforces the same contract whether or not NeMo Guardrails is
/// installed. Fail-closed on any error.
/// </summary>
public sealed class PythonGuardrailClient : IGuardrailClient
{
    private readonly AgentOptions _opts;
    private readonly ILogger<PythonGuardrailClient> _log;

    public PythonGuardrailClient(IOptions<AgentOptions> opts, ILogger<PythonGuardrailClient> log)
    {
        _opts = opts.Value;
        _log = log;
    }

    public Task<GuardrailVerdict> ValidateInputAsync(IDictionary<string, object> request, CancellationToken ct = default) =>
        Invoke("validate_input", request, ct);

    public Task<GuardrailVerdict> ValidateRecommendationAsync(IDictionary<string, object> recommendation, CancellationToken ct = default) =>
        Invoke("validate_recommendation", recommendation, ct);

    public Task<GuardrailVerdict> AuthorizeExecutionAsync(string recommendationId, string approverRole, CancellationToken ct = default) =>
        Invoke("authorize_execution", new Dictionary<string, object>
        {
            ["recommendation_id"] = recommendationId,
            ["approver_role"] = approverRole,
        }, ct);

    private async Task<GuardrailVerdict> Invoke(string method, IDictionary<string, object> payload, CancellationToken ct)
    {
        var psi = new ProcessStartInfo
        {
            FileName = _opts.PythonExecutable,
            WorkingDirectory = Path.Combine(_opts.AgentRoot, "..", "ai-guardrails", "service"),
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add("guardrail_cli.py");
        psi.ArgumentList.Add(method);

        using var proc = Process.Start(psi)!;
        await JsonSerializer.SerializeAsync(proc.StandardInput.BaseStream, payload, cancellationToken: ct);
        proc.StandardInput.Close();
        var json = await proc.StandardOutput.ReadToEndAsync(ct);
        await proc.WaitForExitAsync(ct);
        if (proc.ExitCode != 0)
        {
            var err = await proc.StandardError.ReadToEndAsync(ct);
            _log.LogError("Guardrail call {Method} failed: {Err}", method, err);
            return new GuardrailVerdict(false, "guardrail_error: fail closed");
        }
        using var doc = JsonDocument.Parse(json);
        return new GuardrailVerdict(
            doc.RootElement.GetProperty("allowed").GetBoolean(),
            doc.RootElement.TryGetProperty("reason", out var r) && r.ValueKind == JsonValueKind.String ? r.GetString() : null);
    }
}
