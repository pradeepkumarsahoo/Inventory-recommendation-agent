using FluentValidation;
using FluentValidation.AspNetCore;
using Retail.Api.Middleware;
using Retail.Application.Services;
using Retail.Application.Validators;
using Retail.Infrastructure;
using Serilog;

var builder = WebApplication.CreateBuilder(args);

builder.Host.UseSerilog((ctx, cfg) => cfg
    .ReadFrom.Configuration(ctx.Configuration)
    .Enrich.FromLogContext()
    .WriteTo.Console());

builder.Services.AddControllers();
builder.Services.AddFluentValidationAutoValidation();
builder.Services.AddValidatorsFromAssemblyContaining<ActionExecutionRequestValidator>();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new()
    {
        Title = "Retail Intelligence API",
        Version = "v1",
        Description = "Retail Intelligence & Autonomous Store Decision Platform — Learning Implementation by Pradeep Sahoo.",
    });
});
builder.Services.AddCors(o => o.AddDefaultPolicy(p => p
    .WithOrigins("http://localhost:5173", "http://localhost:4173")
    .AllowAnyHeader()
    .AllowAnyMethod()));
builder.Services.AddRetailInfrastructure(builder.Configuration);
builder.Services.AddScoped<RecommendationService>();

var app = builder.Build();

app.UseSerilogRequestLogging();
app.UseMiddleware<ExceptionMiddleware>();
app.UseCors();
app.UseSwagger();
app.UseSwaggerUI();
app.MapControllers();
app.MapGet("/health", () => Results.Ok(new { status = "ok", service = "retail-api" }));
app.Run();

public partial class Program { }
