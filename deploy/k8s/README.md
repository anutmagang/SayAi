# Kubernetes (Phase 5 — HA / scale)

These manifests are a **starting point** for running SayAi API with multiple replicas behind a Service.

## Assumptions

- You build and push an image (replace `sayai/api:latest` in `deployment.yaml`).
- Secrets (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, provider keys) live in a `Secret` named `sayai-api-secrets` (create separately; do not commit real values).
- PostgreSQL and Redis are managed outside this folder (RDS, ElastiCache, or in-cluster operators).
- For **RAG**, run Qdrant or an external vector store and set `QDRANT_URL` in the Deployment env.

## Stateless API

The FastAPI workers are stateless: session/run state is in Postgres + Redis. You can run **N replicas** and scale with `HorizontalPodAutoscaler` (see `hpa.yaml`).

Use a single Redis and Postgres URL for all replicas. Tune connection pools in the app if you raise replica count.

## Apply

```bash
kubectl apply -f deploy/k8s/base/
```

Review resource requests/limits and the image name before production.

## Optional hardening

- **NetworkPolicy** to restrict egress from API pods (pair with `SKILL_HTTP_HOST_ALLOWLIST`).
- **PodDisruptionBudget** (`pdb.yaml`) so rollouts keep at least one pod available.
- **Ingress** + TLS termination in front of the Service.
