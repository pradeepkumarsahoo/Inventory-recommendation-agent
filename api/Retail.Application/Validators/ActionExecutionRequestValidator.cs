using FluentValidation;
using Retail.Application.Models;

namespace Retail.Application.Validators;

public sealed class ActionExecutionRequestValidator : AbstractValidator<ActionExecutionRequest>
{
    private static readonly HashSet<string> AllowedRoles = new(StringComparer.OrdinalIgnoreCase)
    {
        "sales_associate",
        "store_manager",
        "inventory_manager",
        "regional_manager",
    };

    public ActionExecutionRequestValidator()
    {
        RuleFor(x => x.RecommendationId).NotEmpty().MaximumLength(128);
        RuleFor(x => x.ApproverRole)
            .NotEmpty()
            .Must(r => AllowedRoles.Contains(r))
            .WithMessage("ApproverRole must be one of: " + string.Join(", ", AllowedRoles));
        RuleFor(x => x.Notes).MaximumLength(2000);
    }
}
