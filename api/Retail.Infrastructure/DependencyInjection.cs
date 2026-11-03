using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Retail.Application.Abstractions;
using Retail.Infrastructure.Agents;
using Retail.Infrastructure.Data;
using Retail.Infrastructure.Guardrails;
using Retail.Infrastructure.Options;

namespace Retail.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddRetailInfrastructure(this IServiceCollection services, IConfiguration config)
    {
        services.Configure<DataOptions>(config.GetSection(DataOptions.Section));
        services.Configure<AgentOptions>(config.GetSection(AgentOptions.Section));
        services.AddSingleton<IRetailDataRepository, CsvRetailDataRepository>();
        services.AddSingleton<IRecommendationRepository, InMemoryRecommendationRepository>();
        services.AddSingleton<IAgentOrchestrator, PythonAgentOrchestrator>();
        services.AddSingleton<IGuardrailClient, PythonGuardrailClient>();
        return services;
    }
}
