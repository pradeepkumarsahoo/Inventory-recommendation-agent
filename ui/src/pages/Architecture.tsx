export default function Architecture() {
  return (
    <div className="page-wrap">
      <h1>Architecture &amp; System Design</h1>
      <p className="muted">
        Data layer, service layer, agent orchestration, security boundaries, and the human-in-the-loop approval
        path, as a single annotated diagram.
      </p>

      <section className="card">
        <h3>Technology stack</h3>
        <ul>
          <li>Data: Databricks (Delta Lake · Bronze / Silver / Gold) with a local CSV adapter.</li>
          <li>Service: ASP.NET Core Web API in Clean Architecture (Domain · Application · Infrastructure · Api).</li>
          <li>Agents: Python supervisor + specialists; backend-grounded tool registry; LLM provider abstraction.</li>
          <li>Security: NVIDIA NeMo Guardrails with a local-policy fallback; fail-closed on policy error.</li>
          <li>UI: React 18 · TypeScript · Vite · React Router · Recharts.</li>
          <li>Deployment: Dockerfiles + docker-compose for local development; .env.example in repo root.</li>
        </ul>
      </section>

      <section className="card">
        <h3>Design principles</h3>
        <ul>
          <li>Every recommendation carries its evidence — downstream consumers never re-derive context.</li>
          <li>No LLM may execute SQL or modify inventory directly; agents produce recommendations, humans execute.</li>
          <li>Deterministic fallback behavior so the stack runs without any paid cloud or LLM subscription.</li>
          <li>Append-only audit log for every approved and rejected action.</li>
          <li>Separation of recommendation generation and action execution across trust boundaries.</li>
        </ul>
      </section>

      <section className="iframe-wrap">
        <iframe title="Architecture diagram" src="/docs/architecture-diagram.html" />
      </section>

      <section className="card">
        <h3>Scalability considerations</h3>
        <ul>
          <li>Replace in-memory recommendation repository with EF Core + Postgres for durability.</li>
          <li>Promote the Python agent process to a long-running gRPC/HTTP sidecar when load warrants.</li>
          <li>Front-load aggregations into Delta Gold tables when sales volume grows beyond local-friendly scale.</li>
          <li>Separate guardrail policy service for per-tenant policy versioning.</li>
        </ul>
      </section>

      <footer className="muted">
        Author: Pradeep Sahoo · Learning Implementation ·
        "An AI-powered retail decision intelligence learning implementation demonstrating how Databricks, C#, React,
         Agentic AI, and NVIDIA NeMo Guardrails can work together to transform retail data into measurable store
         business outcomes."
      </footer>
    </div>
  );
}
