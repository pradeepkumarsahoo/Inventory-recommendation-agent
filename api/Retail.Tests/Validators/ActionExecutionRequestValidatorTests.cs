using FluentAssertions;
using FluentValidation.TestHelper;
using Retail.Application.Models;
using Retail.Application.Validators;
using Xunit;

namespace Retail.Tests.Validators;

public class ActionExecutionRequestValidatorTests
{
    private readonly ActionExecutionRequestValidator _v = new();

    [Fact]
    public void Approves_valid_request()
    {
        var r = new ActionExecutionRequest("REC-123", "regional_manager", "ok");
        _v.TestValidate(r).ShouldNotHaveAnyValidationErrors();
    }

    [Fact]
    public void Rejects_unknown_role()
    {
        var r = new ActionExecutionRequest("REC-123", "intern", null);
        _v.TestValidate(r).ShouldHaveValidationErrorFor(x => x.ApproverRole);
    }

    [Fact]
    public void Rejects_empty_recommendation_id()
    {
        var r = new ActionExecutionRequest("", "store_manager", null);
        _v.TestValidate(r).ShouldHaveValidationErrorFor(x => x.RecommendationId);
    }
}
