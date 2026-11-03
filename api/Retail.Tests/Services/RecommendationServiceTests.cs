using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Retail.Application.Abstractions;
using Retail.Application.Models;
using Retail.Application.Services;
using Retail.Domain.Entities;
using Xunit;

namespace Retail.Tests.Services;

public class RecommendationServiceTests
{
    [Fact]
    public async Task ExecuteAction_blocks_when_guardrails_deny()
    {
        var repo = new Mock<IRecommendationRepository>();
        var guardrails = new Mock<IGuardrailClient>();
        var orch = new Mock<IAgentOrchestrator>();
        var rec = new Recommendation
        {
            RecommendationId = "REC-1",
            StoreId = "S101",
            ActionType = "PRICING",
            Title = "x", Justification = "x",
            Priority = "HIGH", RequiredApproval = "regional_manager",
            ResponsibleRole = "pricing_manager", SuccessKpi = "x",
            SourceAgent = "T", CreatedAt = DateTimeOffset.UtcNow,
        };
        repo.Setup(r => r.GetAsync("REC-1", It.IsAny<CancellationToken>())).ReturnsAsync(rec);
        guardrails.Setup(g => g.AuthorizeExecutionAsync("REC-1", "store_manager", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new GuardrailVerdict(false, "insufficient_role"));

        var svc = new RecommendationService(orch.Object, repo.Object, guardrails.Object, NullLogger<RecommendationService>.Instance);
        var resp = await svc.ExecuteActionAsync(new ActionExecutionRequest("REC-1", "store_manager"), "alice");

        resp.Executed.Should().BeFalse();
        resp.Status.Should().Be("blocked");
        repo.Verify(r => r.AppendAuditAsync(It.IsAny<AuditLogEntry>(), It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task ExecuteAction_marks_executed_when_allowed()
    {
        var repo = new Mock<IRecommendationRepository>();
        var guardrails = new Mock<IGuardrailClient>();
        var orch = new Mock<IAgentOrchestrator>();
        var rec = new Recommendation
        {
            RecommendationId = "REC-2",
            StoreId = "S101",
            ActionType = "FRONT_OFFICE",
            Title = "x", Justification = "x",
            Priority = "HIGH", RequiredApproval = "store_manager",
            ResponsibleRole = "store_manager", SuccessKpi = "x",
            SourceAgent = "T", CreatedAt = DateTimeOffset.UtcNow,
        };
        repo.Setup(r => r.GetAsync("REC-2", It.IsAny<CancellationToken>())).ReturnsAsync(rec);
        guardrails.Setup(g => g.AuthorizeExecutionAsync("REC-2", "regional_manager", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new GuardrailVerdict(true, null));

        var svc = new RecommendationService(orch.Object, repo.Object, guardrails.Object, NullLogger<RecommendationService>.Instance);
        var resp = await svc.ExecuteActionAsync(new ActionExecutionRequest("REC-2", "regional_manager"), "bob");

        resp.Executed.Should().BeTrue();
        rec.Status.Should().Be(RecommendationStatus.Executed);
    }
}
