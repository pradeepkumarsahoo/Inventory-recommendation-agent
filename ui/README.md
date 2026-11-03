# Retail Intelligence UI

React 18 + TypeScript + Vite dashboard.

## Run

```bash
npm install
npm run dev
```

Opens on http://localhost:5173 and proxies `/api/*` to
`http://localhost:5080` (configurable in `vite.config.ts`).

## Pages

- `/dashboard` — Executive KPIs + top-impact chart.
- `/products` — Catalog + trending + front-office recommendations.
- `/inventory` — Aging buckets, transfers, replenishment, aging actions.
- `/pricing` — Price recommendations with elasticity & floor annotated.
- `/agents` — Decision center: agent trace, confidence distribution.
- `/game-plan` — Prioritized daily action list.
- `/architecture` — Embedded architecture diagram + description.

## Tests

```bash
npm test
```

Component tests use Vitest + React Testing Library.

Author: Pradeep Sahoo · Learning Implementation
