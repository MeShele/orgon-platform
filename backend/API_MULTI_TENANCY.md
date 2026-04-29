# Multi-tenancy — API surface

The original Phase 1.2 walkthrough of every endpoint and Pydantic model
that lived here has been superseded. Markdown copies of API contracts
inevitably drift from code; the live OpenAPI schema is now the source
of truth.

For the current state:

- **Conceptual overview** of the multi-tenancy model (RLS, partner
  org-scoping, defense-in-depth at the service layer):
  [`../ARCHITECTURE.md` § Multi-tenancy](../ARCHITECTURE.md#multi-tenancy--actual-implementation)
- **Endpoint catalogue** (auth, partner API contract, billing,
  webhooks):
  [`../API.md`](../API.md)
- **Live OpenAPI spec** (always current — generated from FastAPI):
  `GET /api/openapi.json`
- **Pydantic models** are the canonical request/response shapes — read
  them directly under `backend/api/schemas*.py`.

If you find yourself wanting to write up an endpoint contract here,
that's a signal `API.md` needs the section instead. Promote it there.
