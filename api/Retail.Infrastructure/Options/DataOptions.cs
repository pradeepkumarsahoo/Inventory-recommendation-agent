namespace Retail.Infrastructure.Options;

public sealed class DataOptions
{
    public const string Section = "Data";
    public string SampleDataPath { get; set; } = "../databricks/sample-data";
    public string DataSource { get; set; } = "local";   // local | databricks
}

public sealed class AgentOptions
{
    public const string Section = "Agent";
    public string PythonExecutable { get; set; } = "python";
    public string AgentRoot { get; set; } = "../ai-agents";
    public int TimeoutSeconds { get; set; } = 60;
}
