using System.Net;
using System.Text.Json;

namespace Retail.Api.Middleware;

public sealed class ExceptionMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ExceptionMiddleware> _log;

    public ExceptionMiddleware(RequestDelegate next, ILogger<ExceptionMiddleware> log)
    {
        _next = next;
        _log = log;
    }

    public async Task InvokeAsync(HttpContext ctx)
    {
        try
        {
            await _next(ctx);
        }
        catch (ValidationException vex)
        {
            _log.LogWarning(vex, "Validation failure on {Path}", ctx.Request.Path);
            await WriteProblem(ctx, HttpStatusCode.BadRequest, "validation_error", vex.Message);
        }
        catch (KeyNotFoundException knf)
        {
            await WriteProblem(ctx, HttpStatusCode.NotFound, "not_found", knf.Message);
        }
        catch (UnauthorizedAccessException ua)
        {
            await WriteProblem(ctx, HttpStatusCode.Forbidden, "forbidden", ua.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Unhandled error on {Path}", ctx.Request.Path);
            await WriteProblem(ctx, HttpStatusCode.InternalServerError, "server_error", "An unexpected error occurred.");
        }
    }

    private static Task WriteProblem(HttpContext ctx, HttpStatusCode status, string code, string message)
    {
        ctx.Response.StatusCode = (int)status;
        ctx.Response.ContentType = "application/problem+json";
        return ctx.Response.WriteAsync(JsonSerializer.Serialize(new
        {
            type = $"https://retail-platform/problems/{code}",
            title = code,
            status = (int)status,
            detail = message,
        }));
    }
}

public sealed class ValidationException : Exception
{
    public ValidationException(string message) : base(message) { }
}
