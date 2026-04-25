# Skill packs (Phase 5)

Each pack is a directory containing `manifest.json`. Packs may only **reuse built-in handlers** via `extends_skill_id` (no arbitrary code). The API loads packs from:

1. `packages/backend/skill_packs/*/manifest.json` (shipped examples)
2. Extra directories from the env var `SKILL_PACKS_EXTRA_DIRS` (comma-separated absolute paths)

Manifest shape:

```json
{
  "pack_id": "my_org.tools",
  "version": "1.0.0",
  "title": "Human title",
  "skills": [
    {
      "id": "my_org.safe_fetch",
      "extends_skill_id": "sayai.http_get",
      "description": "Optional override text",
      "parameters": { }
    }
  ]
}
```

Skill `id` must match `^[a-z][a-z0-9._-]{1,127}$` and cannot collide with built-ins or other loaded skills.

For stricter HTTP tooling, set `SKILL_HTTP_HOST_ALLOWLIST` on the API (comma-separated hostnames).
