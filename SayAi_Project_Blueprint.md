# SayAi — AI Agentic Coding Platform
### Blueprint Lengkap: Arsitektur, Fitur, Komponen, SkillHunter, Installer & Prompt

> **Versi dokumen:** 1.0.0  
> **Status:** Draft blueprint  
> **Bahasa implementasi:** Python 3.12+  
> **Lisensi target:** MIT (open source)

---

## Daftar Isi

1. [Visi & Misi](#1-visi--misi)
2. [Perbandingan dengan Kompetitor](#2-perbandingan-dengan-kompetitor)
3. [Arsitektur Sistem — Gambaran Besar](#3-arsitektur-sistem--gambaran-besar)
4. [Layer 1 — CLI / TUI Interface](#4-layer-1--cli--tui-interface)
5. [Layer 2 — Orchestrator & DAG Executor](#5-layer-2--orchestrator--dag-executor)
6. [Layer 3 — Agent Pool (Multi-Agent Paralel)](#6-layer-3--agent-pool-multi-agent-paralel)
7. [Layer 4 — Memory System](#7-layer-4--memory-system)
8. [Layer 5 — Tool Layer & MCP Bridge](#8-layer-5--tool-layer--mcp-bridge)
9. [Layer 6 — Custom LLMClient](#9-layer-6--custom-llmclient)
10. [Layer 7 — LiteLLM + Provider Support](#10-layer-7--litellm--provider-support)
11. [SkillHunter — Auto Skill Discovery](#11-skillhunter--auto-skill-discovery)
12. [Admin Approval Workflow](#12-admin-approval-workflow)
13. [Skill Store & Database Schema](#13-skill-store--database-schema)
14. [OneClick Installer (install.sh)](#14-oneclick-installer-installsh)
15. [Struktur Folder Lengkap](#15-struktur-folder-lengkap)
16. [Tech Stack](#16-tech-stack)
17. [Konfigurasi (settings.yaml)](#17-konfigurasi-settingsyaml)
18. [Roadmap Pengembangan](#18-roadmap-pengembangan)
19. [Prompt Library — Semua System Prompt](#19-prompt-library--semua-system-prompt)
20. [Contoh Kode Implementasi](#20-contoh-kode-implementasi)

---

## 1. Visi & Misi

**SayAi** adalah open-source agentic coding CLI dan platform yang dirancang untuk melampaui OpenCode, Aider, dan Claude Code dengan kemampuan:

- **Multi-agent paralel** — beberapa agen berjalan bersamaan mengerjakan subtask berbeda
- **Orchestrator cerdas** — AI memecah task kompleks menjadi DAG subtask dan mengeksekusinya
- **Memori jangka panjang** — vector store untuk memahami codebase besar
- **100+ LLM provider** — via kombinasi LiteLLM + custom routing layer
- **SkillHunter** — AI yang otomatis mencari, mengevaluasi, dan mengusulkan skill/tools baru
- **Self-evolving** — semakin dipakai, semakin pintar karena terus menambah skill baru
- **OneClick install** — satu script untuk install semua di local maupun VPS

### Prinsip Desain

```
Powerful tapi simple   → satu command untuk memulai
Open tapi aman         → open source, tapi skill baru perlu approval admin
Modular tapi kohesif   → setiap layer bisa diganti tanpa merusak yang lain
Self-improving         → SkillHunter otomatis menambah kemampuan baru
```

---

## 2. Perbandingan dengan Kompetitor

| Fitur                       | OpenCode | Aider   | Claude Code | **SayAi**  |
|-----------------------------|----------|---------|-------------|------------|
| Multi-agent paralel         | parsial  | —       | —           | **✓ ya**   |
| Orchestrator + DAG          | —        | —       | —           | **✓ ya**   |
| 100+ LLM provider           | ✓        | parsial | —           | **✓ ya**   |
| Long-term memory (vector)   | —        | —       | —           | **✓ ya**   |
| SkillHunter (auto cari)     | —        | —       | —           | **✓ ya**   |
| Admin approval workflow     | —        | —       | —           | **✓ ya**   |
| Smart router per task-type  | —        | —       | —           | **✓ ya**   |
| OneClick installer          | ✓        | parsial | ✓           | **✓ ya**   |
| VPS / systemd daemon mode   | —        | —       | —           | **✓ ya**   |
| MCP extensible              | ✓        | —       | ✓           | **✓ ya**   |
| Reflection / self-correct   | —        | parsial | parsial     | **✓ ya**   |
| Open source                 | ✓        | ✓       | —           | **✓ ya**   |
| Copyright-aware skill mgmt  | —        | —       | —           | **✓ ya**   |

---

## 3. Arsitektur Sistem — Gambaran Besar

```
┌─────────────────────────────────────────────────────────┐
│                   User / Developer                       │
│              CLI · TUI · IDE plugin                      │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                 CLI / TUI Interface                       │
│     Textual TUI · session mgr · /commands · share links  │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                     Orchestrator                         │
│   Planner · DAG executor · task router · aggregator      │
│   reflection · self-correction · session state           │
└────┬──────────┬──────────┬──────────┬───────────────────┘
     │          │          │          │
┌────▼──┐  ┌───▼───┐  ┌───▼───┐  ┌──▼────┐
│ Coder │  │Review │  │Search │  │ Test  │   ← Agent Pool
│ Agent │  │ Agent │  │ Agent │  │ Agent │   (asyncio paralel)
└───────┘  └───────┘  └───────┘  └───────┘
     │          │          │          │
┌────▼──────────▼──────────▼──────────▼───────────────────┐
│            Memory System          │     Tool Layer        │
│  short-term · vector · scratchpad │  bash · fs · git · MCP│
└──────────────────────────┬────────┴──────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                  Custom LLMClient                        │
│   smart router · fallback · hooks · cost tracker         │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│               LiteLLM (unified abstraction)              │
│          100+ provider · streaming · retry               │
└───┬──────────┬──────────┬──────────┬────────────────────┘
    │          │          │          │
┌───▼──┐  ┌───▼──┐  ┌────▼───┐  ┌───▼────────┐
│Claude│  │Gemini│  │OpenRtr │  │Groq · Ollama│
└──────┘  └──────┘  └────────┘  └────────────┘

KOMPONEN TAMBAHAN (berjalan sebagai background service):
┌─────────────────────────────────────────────────────────┐
│                    SkillHunter                           │
│  crawler · analyzer · rewriter · proposal · notifier    │
└──────────────────────────┬──────────────────────────────┘
                           │ proposal
┌──────────────────────────▼──────────────────────────────┐
│                 Admin Review Panel                       │
│         approve / tolak / lihat diff / re-review         │
└──────────────────────────┬──────────────────────────────┘
                           │ approved
┌──────────────────────────▼──────────────────────────────┐
│                   Skill Store (DB)                       │
│         SQLite + filesystem · versioned · searchable     │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Layer 1 — CLI / TUI Interface

### Teknologi
- **Textual** — framework TUI Python (seperti React tapi untuk terminal)
- **Rich** — formatting output terminal
- **Click** — CLI argument parsing

### Fitur TUI
```
/help           → tampilkan semua perintah
/connect        → tambah API key provider baru
/model          → ganti model aktif
/hunt           → jalankan SkillHunter manual
/admin          → buka admin panel (approve/tolak proposal)
/sessions       → lihat semua sesi aktif
/share          → buat link share sesi
/undo           → undo perubahan terakhir
/redo           → redo
/config         → buka editor konfigurasi
```

### Contoh kode CLI entry point

```python
# cli/app.py
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog
from sayai.orchestrator import Orchestrator
from sayai.session import SessionManager

class SayAiApp(App):
    CSS_PATH = "app.tcss"
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+n", "new_session", "New Session"),
        ("ctrl+h", "toggle_history", "History"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="output", highlight=True, markup=True)
        yield Input(placeholder="Ketik task atau /command ...", id="prompt")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted):
        user_input = event.value.strip()
        if not user_input:
            return

        if user_input.startswith("/"):
            await self.handle_command(user_input)
        else:
            await self.run_task(user_input)

    async def run_task(self, task: str):
        orchestrator = Orchestrator()
        async for chunk in orchestrator.stream(task):
            self.query_one("#output", RichLog).write(chunk)
```

---

## 5. Layer 2 — Orchestrator & DAG Executor

### Peran Orchestrator
Orchestrator adalah "otak" SayAi. Ia menerima task kompleks dari user, memecahnya menjadi subtask menggunakan LLM (Planner), membangun dependency graph (DAG), lalu mengeksekusi subtask secara paralel atau berurutan sesuai dependency.

### Alur DAG Execution

```
User task: "Build auth module with tests and security review"
                    │
                    ▼
            ┌───────────────┐
            │   Planner     │  ← LLM decompose task
            └───────┬───────┘
                    │ menghasilkan DAG:
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       Task A    Task B    Task C       ← PARALEL (tidak ada dependency)
    [CoderAgent] [SearchAgent] [ReviewAgent]
    write auth   find JWT lib  security check
          │         │
          └────┬────┘
               ▼
           Task D                       ← SEQUENTIAL (butuh A & B selesai)
          [TestAgent]
          write tests
               │
               ▼
        ┌──────────────┐
        │  Aggregator  │  ← merge, validate, reflect
        └──────────────┘
```

### Contoh kode DAG Executor

```python
# orchestrator/dag.py
import asyncio
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Task:
    id: str
    agent_type: str          # "coder" | "reviewer" | "searcher" | "tester"
    instruction: str
    depends_on: list[str] = field(default_factory=list)
    priority: int = 5        # 1 (tinggi) – 10 (rendah)
    budget: str = "normal"   # "cheap" | "normal" | "premium"
    result: Any = None

class DAGOrchestrator:
    def __init__(self, agent_pool):
        self.pool = agent_pool
        self.results: dict[str, Any] = {}

    async def execute(self, tasks: list[Task]) -> dict:
        pending = {t.id: t for t in tasks}

        while pending:
            # Ambil semua task yang dependency-nya sudah selesai
            ready = [
                t for t in pending.values()
                if all(dep in self.results for dep in t.depends_on)
            ]

            if not ready:
                break  # semua selesai atau ada circular dependency

            # Sort by priority
            ready.sort(key=lambda t: t.priority)

            # Jalankan paralel dengan asyncio.gather
            results = await asyncio.gather(
                *[self.pool.run(task) for task in ready],
                return_exceptions=True
            )

            for task, result in zip(ready, results):
                if isinstance(result, Exception):
                    # Retry atau fallback
                    result = await self.pool.run(task, retry=True)
                self.results[task.id] = result
                del pending[task.id]

        return self.results
```

### Contoh kode Planner

```python
# orchestrator/planner.py
from sayai.llm import LLMClient
import json

PLANNER_SYSTEM_PROMPT = """
Kamu adalah AI planner untuk SayAi coding agent.
Tugasmu: terima task dari user, pecah menjadi subtask spesifik.
Output HARUS berupa JSON array dengan format berikut:
[
  {
    "id": "task_A",
    "agent_type": "coder|reviewer|searcher|tester",
    "instruction": "instruksi spesifik untuk agent",
    "depends_on": [],
    "priority": 1-10,
    "budget": "cheap|normal|premium"
  }
]
Rules:
- Parallelkan task yang tidak saling bergantung
- Gunakan searcher untuk research, coder untuk coding
- Reviewer dan tester selalu setelah coder
- budget "cheap" untuk task sederhana (gunakan Groq/Llama)
- budget "premium" untuk task kompleks (gunakan Claude Sonnet)
Output JSON saja, tidak ada teks lain.
"""

class Planner:
    def __init__(self):
        self.client = LLMClient()

    async def plan(self, user_task: str) -> list[dict]:
        response = await self.client.complete(
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Task: {user_task}"}
            ],
            task_type="planning",
        )
        return json.loads(response)
```

---

## 6. Layer 3 — Agent Pool (Multi-Agent Paralel)

### Jenis Agent

| Agent         | Tanggung Jawab                                      |
|---------------|-----------------------------------------------------|
| CoderAgent    | Menulis kode, patch file, refactor                  |
| ReviewerAgent | Code review, critic, security check, PR review      |
| SearcherAgent | Web search, docs search, RAG ke codebase            |
| TesterAgent   | Tulis unit test, jalankan test, buat coverage report|
| PlannerAgent  | Sub-planning untuk task yang sangat kompleks        |

### Contoh kode BaseAgent

```python
# agents/base.py
from abc import ABC, abstractmethod
from sayai.llm import LLMClient
from sayai.memory import ContextManager
from sayai.tools import ToolExecutor

class BaseAgent(ABC):
    def __init__(self, agent_id: str):
        self.id = agent_id
        self.llm = LLMClient()
        self.context = ContextManager(agent_id)
        self.tools = ToolExecutor()
        self.max_iterations = 10

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        ...

    @abstractmethod
    async def run(self, task: str, context: dict = {}) -> str:
        ...

    async def think_and_act(self, task: str) -> str:
        """ReAct loop: Reason → Act → Observe → Repeat"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task}
        ]

        for i in range(self.max_iterations):
            response = await self.llm.complete(messages=messages)

            # Cek apakah ada tool call
            if "<tool>" in response:
                tool_result = await self.tools.execute(response)
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "tool", "content": tool_result})
            else:
                # Agent selesai
                return response

        return "Max iterations reached"
```

### Contoh kode CoderAgent

```python
# agents/coder.py
from .base import BaseAgent

class CoderAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return """
Kamu adalah CoderAgent dari SayAi — expert software engineer.
Kemampuanmu:
- Menulis kode bersih, terstruktur, dan terdokumentasi
- Membaca dan memahami codebase yang sudah ada
- Membuat patch/diff yang minimal dan tepat sasaran
- Mengikuti konvensi kode yang sudah ada di project

Tools yang tersedia:
- read_file(path) → baca isi file
- write_file(path, content) → tulis/overwrite file
- patch_file(path, diff) → apply patch ke file
- bash(command) → jalankan command bash
- search_codebase(query) → cari di codebase

Format tool call:
<tool>nama_tool</tool>
<args>{"param": "value"}</args>

Selalu baca file yang relevan sebelum menulis kode.
Jangan mengubah file yang tidak perlu diubah.
"""

    async def run(self, task: str, context: dict = {}) -> str:
        enriched_task = f"""
Task: {task}
Context: {context.get('summary', 'tidak ada')}
Working dir: {context.get('cwd', '.')}
"""
        return await self.think_and_act(enriched_task)
```

---

## 7. Layer 4 — Memory System

### Tiga Lapis Memory

```
┌─────────────────────────────────────────────────────────┐
│  SHORT-TERM (per agent, per session)                     │
│  - Sliding window context (8000 token default)           │
│  - Disimpan in-memory selama sesi aktif                  │
│  - Auto-summarize jika melebihi batas                    │
├─────────────────────────────────────────────────────────┤
│  LONG-TERM (shared, persistent)                          │
│  - Vector store: Qdrant                                  │
│  - Menyimpan: kode, docs, keputusan penting, error log   │
│  - Diindex otomatis saat agent write/read file           │
│  - Bisa di-query: "kode auth yang pernah kita tulis"     │
├─────────────────────────────────────────────────────────┤
│  WORKING MEMORY (shared scratchpad, per task)            │
│  - Shared state antar agent dalam satu DAG               │
│  - Contoh: SearchAgent simpan "JWT terbaik = jose"       │
│            CoderAgent baca → pakai jose                  │
│  - Disimpan di Redis (fast, ephemeral)                   │
└─────────────────────────────────────────────────────────┘
```

### Contoh kode Memory System

```python
# memory/context.py
from collections import deque
from sayai.llm import LLMClient

class ContextManager:
    def __init__(self, agent_id: str, max_tokens: int = 8000):
        self.agent_id = agent_id
        self.max_tokens = max_tokens
        self.messages: deque = deque()
        self.llm = LLMClient()

    def add(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self._trim_if_needed()

    def _trim_if_needed(self):
        """Jika context terlalu panjang, summarize bagian lama"""
        total = sum(len(m["content"]) // 4 for m in self.messages)
        if total > self.max_tokens:
            # Ambil 20 pesan pertama untuk disummarise
            old = list(self.messages)[:20]
            self.messages = deque(list(self.messages)[20:])
            # Summary async (simplified)
            summary = f"[Summary dari {len(old)} pesan sebelumnya]"
            self.messages.appendleft({"role": "system", "content": summary})

    def get_messages(self) -> list:
        return list(self.messages)

# memory/vector.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

class VectorMemory:
    def __init__(self, url: str = "http://localhost:6333"):
        self.client = QdrantClient(url=url)
        self._ensure_collection()

    def _ensure_collection(self):
        collections = [c.name for c in self.client.get_collections().collections]
        if "sayai_memory" not in collections:
            self.client.create_collection(
                collection_name="sayai_memory",
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )

    async def store(self, content: str, metadata: dict):
        embedding = await self._embed(content)
        self.client.upsert(
            collection_name="sayai_memory",
            points=[PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={**metadata, "content": content}
            )]
        )

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        embedding = await self._embed(query)
        results = self.client.search(
            collection_name="sayai_memory",
            query_vector=embedding,
            limit=top_k
        )
        return [{"content": r.payload["content"], "score": r.score} for r in results]

    async def _embed(self, text: str) -> list[float]:
        import litellm
        response = await litellm.aembedding(model="text-embedding-3-small", input=text)
        return response.data[0]["embedding"]
```

---

## 8. Layer 5 — Tool Layer & MCP Bridge

### Daftar Tools Bawaan

| Tool               | Fungsi                                              |
|--------------------|-----------------------------------------------------|
| `bash(cmd)`        | Jalankan command bash (sandboxed)                   |
| `read_file(path)`  | Baca isi file                                       |
| `write_file()`     | Tulis/overwrite file                                |
| `patch_file()`     | Apply diff/patch ke file                            |
| `list_dir(path)`   | List isi direktori                                  |
| `search_code(q)`   | Grep/ripgrep di codebase                            |
| `git_diff()`       | Lihat git diff                                      |
| `git_commit(msg)`  | Commit perubahan                                    |
| `web_search(q)`    | Search web                                          |
| `fetch_url(url)`   | Ambil konten URL                                    |
| `run_tests()`      | Jalankan test suite                                 |
| `lint(path)`       | Jalankan linter                                     |
| `mcp_call()`       | Forward ke MCP server eksternal                     |

### Contoh kode Tool Executor

```python
# tools/executor.py
import json
import re
import subprocess
from pathlib import Path

class ToolExecutor:
    async def execute(self, llm_response: str) -> str:
        """Parse tool call dari response LLM dan eksekusi"""
        tool_match = re.search(r"<tool>(.*?)</tool>", llm_response, re.DOTALL)
        args_match = re.search(r"<args>(.*?)</args>", llm_response, re.DOTALL)

        if not tool_match:
            return ""

        tool_name = tool_match.group(1).strip()
        args = json.loads(args_match.group(1)) if args_match else {}

        handler = getattr(self, f"tool_{tool_name}", None)
        if not handler:
            return f"Error: tool '{tool_name}' tidak ditemukan"

        return await handler(**args)

    async def tool_bash(self, command: str, timeout: int = 30) -> str:
        """Jalankan bash command dengan timeout"""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True,
                text=True, timeout=timeout
            )
            output = result.stdout or result.stderr
            return output[:5000]  # batasi output
        except subprocess.TimeoutExpired:
            return f"Error: command timeout setelah {timeout}s"

    async def tool_read_file(self, path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8")
        except Exception as e:
            return f"Error: {e}"

    async def tool_write_file(self, path: str, content: str) -> str:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding="utf-8")
            return f"OK: file ditulis ke {path}"
        except Exception as e:
            return f"Error: {e}"

# tools/mcp_bridge.py
import httpx

class MCPBridge:
    """Jembatan ke MCP (Model Context Protocol) servers eksternal"""
    def __init__(self, servers: list[dict]):
        self.servers = {s["name"]: s["url"] for s in servers}

    async def call(self, server: str, tool: str, args: dict) -> str:
        url = self.servers.get(server)
        if not url:
            return f"Error: MCP server '{server}' tidak terdaftar"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{url}/tools/{tool}",
                json=args, timeout=30
            )
            return resp.text
```

---

## 9. Layer 6 — Custom LLMClient

### Arsitektur Custom LLMClient

```
User request
    │
    ▼
┌─────────────────────────────────┐
│     Pre-hooks (before LLM)      │
│  - inject system context        │
│  - log request                  │
│  - rate limit check             │
└───────────────┬─────────────────┘
                │
    ┌───────────▼────────────┐
    │     Smart Router       │
    │  task_type → model     │
    │  budget → provider     │
    └───────────┬────────────┘
                │
    ┌───────────▼────────────┐
    │   Fallback Chain       │
    │  primary → backup      │
    │  retry on error        │
    └───────────┬────────────┘
                │
    ┌───────────▼────────────┐
    │       LiteLLM          │
    │   actual API call      │
    └───────────┬────────────┘
                │
┌───────────────▼─────────────────┐
│     Post-hooks (after LLM)      │
│  - log response + cost          │
│  - cache result                 │
│  - update metrics               │
└─────────────────────────────────┘
```

### Contoh kode LLMClient

```python
# llm/client.py
import litellm
from sayai.llm.router import SmartRouter
from sayai.llm.hooks import HookChain

class LLMClient:
    def __init__(self, config: dict = {}):
        self.router = SmartRouter()
        self.hooks = HookChain([
            LoggingHook(),
            CostTrackingHook(),
            CachingHook(),
        ])

    async def complete(
        self,
        messages: list,
        task_type: str = "default",
        budget: str = "normal",
        stream: bool = False,
        **kwargs
    ) -> str:
        # Pre-hooks
        messages = await self.hooks.before(messages, task_type=task_type)

        # Route ke model
        model = self.router.route(task_type=task_type, budget=budget)
        fallbacks = self.router.get_fallback(model)

        # LiteLLM call dengan fallback
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                fallbacks=fallbacks,
                **kwargs
            )
        except Exception as e:
            raise RuntimeError(f"Semua provider gagal: {e}")

        result = response.choices[0].message.content

        # Post-hooks
        result = await self.hooks.after(result, response=response)
        return result

# llm/router.py
class SmartRouter:
    ROUTING_TABLE = {
        "planning":    "claude-sonnet-4-20250514",
        "coding":      "openrouter/deepseek/deepseek-coder-v2",
        "reviewing":   "claude-sonnet-4-20250514",
        "searching":   "groq/llama-3.3-70b-versatile",
        "testing":     "openrouter/deepseek/deepseek-coder-v2",
        "cheap":       "groq/llama-3.3-70b-versatile",
        "default":     "claude-haiku-4-5-20251001",
    }

    FALLBACK_CHAINS = {
        "claude-sonnet-4-20250514": [
            "gemini/gemini-2.5-pro",
            "openrouter/anthropic/claude-sonnet-4",
            "groq/llama-3.3-70b-versatile",
        ],
        "openrouter/deepseek/deepseek-coder-v2": [
            "groq/llama-3.3-70b-versatile",
            "claude-haiku-4-5-20251001",
        ],
    }

    def route(self, task_type: str, budget: str = "normal") -> str:
        if budget == "cheap":
            return self.ROUTING_TABLE["cheap"]
        return self.ROUTING_TABLE.get(task_type, self.ROUTING_TABLE["default"])

    def get_fallback(self, model: str) -> list:
        return self.FALLBACK_CHAINS.get(model, [])
```

---

## 10. Layer 7 — LiteLLM + Provider Support

LiteLLM digunakan sebagai unified abstraction layer. Custom LLMClient duduk di atasnya untuk menambahkan logika routing, fallback, dan hooks.

### Provider yang Didukung (via LiteLLM)

| Provider          | Contoh Model                          | Catatan                    |
|-------------------|---------------------------------------|----------------------------|
| Anthropic         | claude-sonnet-4-20250514              | Best untuk planning/review |
| OpenAI            | gpt-4o, gpt-4o-mini                   |                            |
| Google Gemini     | gemini/gemini-2.5-pro                 | Best untuk coding lama     |
| OpenRouter        | openrouter/deepseek/deepseek-coder-v2 | Akses 100+ model           |
| Groq              | groq/llama-3.3-70b-versatile          | Tercepat untuk simple task |
| Mistral           | mistral/mistral-large                 |                            |
| AWS Bedrock       | bedrock/anthropic.claude-3-5-sonnet   |                            |
| Azure OpenAI      | azure/gpt-4o                          |                            |
| Ollama (local)    | ollama/llama3.2, ollama/codestral     | Gratis, privasi terjaga    |
| LM Studio (local) | openai/local-model                    |                            |
| DeepSeek          | deepseek/deepseek-coder               |                            |
| Cohere            | command-r-plus                        |                            |
| + 90 lainnya      | via LiteLLM                           |                            |

### Konfigurasi provider di settings.yaml

```yaml
llm:
  providers:
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
      default_model: claude-haiku-4-5-20251001

    openrouter:
      api_key: ${OPENROUTER_API_KEY}
      base_url: https://openrouter.ai/api/v1

    groq:
      api_key: ${GROQ_API_KEY}

    ollama:
      base_url: http://localhost:11434
      # tidak perlu API key
```

---

## 11. SkillHunter — Auto Skill Discovery

### Konsep

SkillHunter adalah agent khusus yang berjalan sebagai background service. Tugasnya adalah:

1. **Crawl** sumber terbuka dan berbayar secara otomatis (GitHub, PyPI, npm, MCP registry, HuggingFace, RSS, dll.)
2. **Analyze** setiap item — relevance score, license check, safety check, duplicate check
3. **Rewrite** ke format SKILL.md standar SayAi, dengan copyright dicantumkan
4. **Propose** ke admin melalui TUI dan/atau webhook
5. **Tunggu approval** — admin approve atau tolak
6. **Store** jika diapprove — masuk ke Skill Store, langsung aktif

### Alur SkillHunter

```
Scheduler (cron / manual /hunt)
         │
         ▼
┌─────────────────────────────────┐
│  Crawler (paralel, async)        │
│  - GitHub: search "mcp server"   │
│  - PyPI: tags [agent, tool, ai]  │
│  - npm: keywords [mcp, agent]    │
│  - MCP Registry (registry.mcp)   │
│  - HuggingFace papers RSS        │
│  - Blog feed / RSS kustom        │
└───────────────┬─────────────────┘
                │ raw items
                ▼
┌─────────────────────────────────┐
│  AI Analyzer                     │
│  - relevance score (0.0–1.0)     │
│  - duplicate check (vector sim)  │
│  - license scan (MIT/Apache/GPL) │
│  - safety check (no malware)     │
│  - compatibility check           │
│  → skip jika score < 0.6         │
│  → skip jika lisensi tidak jelas │
└───────────────┬─────────────────┘
                │ filtered items
                ▼
┌─────────────────────────────────┐
│  AI Rewriter                     │
│  - convert ke format SKILL.md    │
│  - cantumkan: copyright, source  │
│  - cantumkan: license, version   │
│  - tulis: description, usage     │
│  - tulis: triggers, examples     │
└───────────────┬─────────────────┘
                │ skill draft
                ▼
┌─────────────────────────────────┐
│  Proposal Generator              │
│  - simpan ke DB status=pending   │
│  - notifikasi admin (TUI/webhook)│
│  - tampilkan: preview + diff     │
└───────────────┬─────────────────┘
                │
        ┌───────▼────────┐
        │  Admin Review  │
        │  approve/tolak │
        └───────┬────────┘
       ┌────────┴────────┐
       ▼                 ▼
  Approved            Rejected
  → Skill Store      → Quarantine
  → langsung aktif   → logged, bisa re-review
```

### Contoh kode SkillHunter

```python
# skillhunter/hunter.py
import asyncio
from sayai.llm import LLMClient
from sayai.skillhunter.crawlers import GitHubCrawler, PyPICrawler, MCPCrawler
from sayai.skillhunter.analyzer import SkillAnalyzer
from sayai.skillhunter.rewriter import SkillRewriter
from sayai.db import SkillDB

class SkillHunter:
    def __init__(self, config: dict):
        self.config = config
        self.crawlers = [
            GitHubCrawler(query="mcp server tool"),
            PyPICrawler(tags=["agent", "tool", "mcp"]),
            MCPCrawler(url="https://registry.mcp.dev"),
        ]
        self.analyzer = SkillAnalyzer()
        self.rewriter = SkillRewriter()
        self.db = SkillDB()

    async def hunt(self):
        """Main hunt loop"""
        print("[SkillHunter] Memulai pencarian skill baru...")

        # 1. Crawl semua sumber paralel
        raw_results = await asyncio.gather(
            *[crawler.crawl() for crawler in self.crawlers],
            return_exceptions=True
        )
        items = [item for batch in raw_results
                 if not isinstance(batch, Exception)
                 for item in batch]

        print(f"[SkillHunter] Ditemukan {len(items)} kandidat")

        # 2. Proses setiap item
        for item in items:
            try:
                await self._process_item(item)
            except Exception as e:
                print(f"[SkillHunter] Error processing {item.name}: {e}")

    async def _process_item(self, item):
        # Cek duplikat di DB
        if await self.db.exists(url=item.url):
            return

        # Analyze
        analysis = await self.analyzer.analyze(item)
        if analysis.score < 0.6:
            return
        if analysis.license in ("unknown", "proprietary", "no-license"):
            print(f"[SKIP] {item.name}: lisensi tidak jelas")
            return

        # Rewrite ke format SKILL.md
        skill_md = await self.rewriter.rewrite(
            source=item,
            analysis=analysis,
        )

        # Simpan proposal ke DB
        await self.db.save_proposal({
            "name": item.name,
            "version": item.version,
            "source_url": item.url,
            "license": analysis.license,
            "copyright": analysis.copyright,
            "score": analysis.score,
            "content": skill_md,
            "status": "pending",
            "tags": analysis.tags,
        })

        print(f"[SkillHunter] Proposal baru: {item.name} (score: {analysis.score:.2f})")

# skillhunter/rewriter.py — prompt untuk rewriter ada di Section 19
class SkillRewriter:
    def __init__(self):
        self.llm = LLMClient()

    async def rewrite(self, source, analysis) -> str:
        prompt = f"""
Sumber: {source.name} v{source.version}
URL: {source.url}
Lisensi: {analysis.license}
Copyright: {analysis.copyright}
Deskripsi asli: {source.description}
README (ringkasan): {source.readme[:2000]}

Tulis ulang sebagai SayAi SKILL.md dengan format berikut.
"""
        return await self.llm.complete(
            messages=[
                {"role": "system", "content": SKILLHUNTER_REWRITER_PROMPT},
                {"role": "user", "content": prompt}
            ],
            task_type="default",
        )
```

---

## 12. Admin Approval Workflow

### Alur Detail Admin

```
SkillHunter simpan proposal (status=pending)
         │
         ▼ notifikasi
Admin buka panel: sayai admin
         │
         ▼
Tampil daftar proposals:
┌──────────────────────────────────────────────────────┐
│ [PENDING] browser-automation v1.2.0   score: 0.91   │
│ Source: github.com/x/playwright-mcp · MIT           │
│ Tags: browser · automation · playwright             │
│ Copyright: 2024 John Doe                            │
│                                                      │
│  [Approve]  [Tolak]  [Lihat Diff]  [Detail]         │
├──────────────────────────────────────────────────────┤
│ [PENDING] sql-optimizer v0.3.1        score: 0.78   │
│ Source: PyPI · Apache-2.0                           │
│  [Approve]  [Tolak]  [Lihat Diff]  [Detail]         │
├──────────────────────────────────────────────────────┤
│ [APPROVED] image-gen-helper v2.0.0   approved 2h ago│
├──────────────────────────────────────────────────────┤
│ [REJECTED] scraper-toolkit v1.0.0   lisensi unclear │
└──────────────────────────────────────────────────────┘
```

### Aksi Admin

- **Approve** → skill dipindah ke Skill Store, status=approved, langsung aktif digunakan agen
- **Tolak** → skill dipindah ke quarantine, status=rejected, alasan dicatat
- **Lihat Diff** → tampil SKILL.md dalam format diff untuk review konten
- **Detail** → buka README asli, copyright info, dependency analysis
- **Re-review** → skill rejected bisa diajukan ulang setelah perbaikan
- **Edit** → admin bisa edit SKILL.md sebelum approve

### Notifikasi Channel

```yaml
# config/settings.yaml
admin:
  notify:
    - type: tui          # notifikasi langsung di TUI
    - type: webhook
      url: https://hooks.slack.com/xxx  # opsional: Slack
    - type: email
      to: admin@company.com            # opsional: email
```

---

## 13. Skill Store & Database Schema

### Schema Database (SQLite)

```sql
-- Skill store utama
CREATE TABLE skills (
    id          TEXT PRIMARY KEY,       -- uuid
    name        TEXT NOT NULL,
    version     TEXT,
    source_url  TEXT,
    license     TEXT,
    copyright   TEXT,
    content     TEXT,                  -- isi SKILL.md
    score       REAL,                  -- 0.0–1.0
    status      TEXT DEFAULT 'pending', -- pending/approved/rejected
    tags        TEXT,                  -- JSON array
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME,
    approved_by TEXT,
    approved_at DATETIME,
    reject_reason TEXT
);

-- Sumber crawl
CREATE TABLE skill_sources (
    id          TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    type        TEXT,                  -- github/pypi/npm/mcp/rss
    enabled     BOOLEAN DEFAULT TRUE,
    last_run    DATETIME,
    total_found INTEGER DEFAULT 0
);

-- Log hunt activity
CREATE TABLE hunt_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_type TEXT,
    items_found INTEGER,
    items_passed INTEGER,
    items_proposed INTEGER,
    error       TEXT
);

-- Usage tracking (skill mana yang sering dipakai)
CREATE TABLE skill_usage (
    skill_id    TEXT REFERENCES skills(id),
    used_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent_type  TEXT,
    task_type   TEXT
);
```

### Format SKILL.md

Setiap skill yang masuk ke Skill Store disimpan dalam format SKILL.md berikut:

```markdown
---
name: browser-automation
version: 1.2.0
source: https://github.com/x/playwright-mcp
license: MIT
copyright: "2024 John Doe — https://github.com/johndoe"
score: 0.91
tags: [browser, automation, e2e, playwright]
approved_at: 2025-01-15T10:30:00Z
approved_by: admin
---

# Browser automation skill

Skill ini memungkinkan SayAi untuk mengontrol browser secara otomatis
menggunakan Playwright. Berguna untuk web scraping, testing UI, dan
otomasi workflow berbasis browser.

## Kapan digunakan (triggers)

Gunakan skill ini ketika:
- User meminta untuk scraping website
- User meminta untuk testing UI/frontend
- User meminta untuk otomasi form atau login
- Task membutuhkan interaksi dengan halaman web

## Tools yang tersedia

- `browser_open(url)` — buka URL di browser
- `browser_click(selector)` — klik elemen
- `browser_type(selector, text)` — ketik teks
- `browser_screenshot()` — ambil screenshot
- `browser_extract(selector)` — extract teks dari elemen

## Contoh penggunaan

```python
# Buka halaman dan extract data
browser_open("https://example.com/data")
data = browser_extract(".main-content")
```

## Dependensi

- playwright>=1.40.0 (diinstall otomatis)
- Python 3.10+

## Catatan copyright

Skill ini diadaptasi dari playwright-mcp oleh John Doe.
Lisensi asli: MIT. Copyright 2024 John Doe.
Semua perubahan oleh SayAi team dilisensikan di bawah MIT yang sama.
```

---

## 14. OneClick Installer (install.sh)

### Cara Install

```bash
# Install standar (local/laptop)
curl -fsSL https://sayai.dev/install.sh | bash

# Install untuk VPS (dengan systemd daemon)
curl -fsSL https://sayai.dev/install.sh | bash -s -- --vps

# Install minimal (tanpa Qdrant dan Ollama)
curl -fsSL https://sayai.dev/install.sh | bash -s -- --minimal

# Install untuk development/kontribusi
curl -fsSL https://sayai.dev/install.sh | bash -s -- --dev
```

### Apa yang Dilakukan installer.sh

```
STEP 1: Deteksi environment
  - OS: Ubuntu/Debian/Arch/Fedora/macOS
  - Architecture: x86_64 / arm64
  - Python version check
  - Disk space check (min 2GB)
  - VPS vs local detection

STEP 2: Install system dependencies
  - Python 3.12 (jika belum ada)
  - git, curl, wget, build-essential
  - sqlite3
  - redis-server
  - uv (Python package manager — pengganti pip/venv)

STEP 3: Clone & install SayAi
  - git clone sayai repository
  - uv sync (install semua Python packages)
  - Packages: litellm, textual, qdrant-client, pydantic,
              anyio, rich, httpx, aiosqlite, click, ...

STEP 4: Setup optional services
  - Qdrant vector DB (untuk long-term memory)
  - Ollama (untuk local LLM, user pilih)
  - Pilih model Ollama default (llama3.2:3b — ringan)
  - Start Redis service

STEP 5: Interactive config wizard
  - Masukkan API key (Anthropic, OpenRouter, Groq, dll.)
  - Pilih default model
  - Set admin password untuk approval panel
  - Simpan ke ~/.config/sayai/.env (chmod 600)

STEP 6: VPS extras (jika --vps)
  - Buat systemd service file
  - Enable autostart on boot
  - Setup log rotation

STEP 7: Inisialisasi database
  - sayai db init (buat tabel SQLite)
  - Import skill bawaan (built-in skills)

STEP 8: Add ke PATH
  - Tambah alias sayai ke ~/.bashrc atau ~/.zshrc

SELESAI: Tampilkan ringkasan dan cara mulai
```

### Isi install.sh

```bash
#!/usr/bin/env bash
# =============================================================
# SayAi — OneClick Installer v1.0
# Usage: curl -fsSL https://sayai.dev/install.sh | bash
#        bash install.sh [--vps] [--minimal] [--dev]
# =============================================================
set -euo pipefail

# ── Variabel ────────────────────────────────────────────────
SAYAI_REPO="https://github.com/sayai-dev/sayai"
SAYAI_DIR="$HOME/.sayai"
SAYAI_CONFIG="$HOME/.config/sayai"
SAYAI_DATA="$HOME/.local/share/sayai"
MODE="local"

for arg in "$@"; do
  case $arg in
    --vps)     MODE="vps" ;;
    --minimal) MODE="minimal" ;;
    --dev)     MODE="dev" ;;
  esac
done

# ── Colors ──────────────────────────────────────────────────
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'
B='\033[0;34m'; BOLD='\033[1m'; N='\033[0m'

info()    { echo -e "${B}[SayAi]${N} $1"; }
success() { echo -e "${G}[OK]${N} $1"; }
warn()    { echo -e "${Y}[WARN]${N} $1"; }
err()     { echo -e "${R}[ERROR]${N} $1"; exit 1; }
step()    { echo -e "\n${BOLD}── $1 ──${N}"; }

# ── Banner ──────────────────────────────────────────────────
echo -e "${BOLD}${B}"
echo "  ███████╗ █████╗ ██╗   ██╗ █████╗ ██╗"
echo "  ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗██║"
echo "  ███████╗███████║ ╚████╔╝ ███████║██║"
echo "  ╚════██║██╔══██║  ╚██╔╝  ██╔══██║██║"
echo "  ███████║██║  ██║   ██║   ██║  ██║██║"
echo "  ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝"
echo -e "${N}  AI Agentic Coding Platform — mode: ${Y}$MODE${N}"
echo ""

# ── STEP 1: Deteksi OS ──────────────────────────────────────
step "1/7 Deteksi environment"
OS=""; PKG_MGR=""
if   [[ -f /etc/debian_version ]]; then OS="debian"; PKG_MGR="apt"
elif [[ -f /etc/arch-release ]];   then OS="arch";   PKG_MGR="pacman"
elif [[ -f /etc/fedora-release ]]; then OS="fedora"; PKG_MGR="dnf"
elif [[ "$(uname)" == "Darwin" ]]; then OS="macos";  PKG_MGR="brew"
else err "OS tidak dikenali."; fi

ARCH=$(uname -m)
info "OS: $OS | Arch: $ARCH | Mode: $MODE"

# Cek disk space (min 2GB)
AVAIL=$(df -BG "$HOME" | awk 'NR==2{print $4}' | tr -d 'G')
[[ "$AVAIL" -lt 2 ]] && warn "Disk kurang dari 2GB. Mungkin ada masalah."

# ── STEP 2: System dependencies ─────────────────────────────
step "2/7 Install system dependencies"

install_debian() {
  sudo apt-get update -q
  sudo apt-get install -y python3.12 python3.12-venv python3-pip \
    git curl wget build-essential sqlite3 redis-server ca-certificates
}
install_arch() {
  sudo pacman -Sy --noconfirm python git curl base-devel sqlite redis
}
install_macos() {
  command -v brew &>/dev/null || \
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  brew install python@3.12 git redis sqlite
}
install_fedora() {
  sudo dnf install -y python3.12 git curl sqlite redis
}

case $OS in
  debian) install_debian ;;
  arch)   install_arch ;;
  macos)  install_macos ;;
  fedora) install_fedora ;;
esac
success "System dependencies selesai"

# Install uv
if ! command -v uv &>/dev/null; then
  info "Menginstall uv (Python package manager)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"
  echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "${HOME}/.bashrc"
fi
success "uv: $(uv --version)"

# ── STEP 3: Clone & install SayAi ───────────────────────────
step "3/7 Install SayAi"
mkdir -p "$SAYAI_DIR" "$SAYAI_CONFIG" "$SAYAI_DATA"

if [[ -d "$SAYAI_DIR/.git" ]]; then
  info "Update SayAi..."
  git -C "$SAYAI_DIR" pull --ff-only
else
  info "Clone SayAi dari $SAYAI_REPO..."
  git clone "$SAYAI_REPO" "$SAYAI_DIR"
fi

cd "$SAYAI_DIR"
if [[ "$MODE" == "dev" ]]; then
  uv sync --all-extras
else
  uv sync
fi
success "Python packages terinstall"

# ── STEP 4: Optional services ────────────────────────────────
step "4/7 Setup optional services"

# Qdrant
if [[ "$MODE" != "minimal" ]]; then
  QDRANT_VERSION="v1.9.2"
  QDRANT_BIN="$SAYAI_DATA/bin/qdrant"
  if [[ ! -f "$QDRANT_BIN" ]]; then
    info "Menginstall Qdrant vector DB..."
    mkdir -p "$SAYAI_DATA/bin"
    QDRANT_URL="https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant-x86_64-unknown-linux-musl.tar.gz"
    curl -L "$QDRANT_URL" | tar -xz -C "$SAYAI_DATA/bin/"
    chmod +x "$QDRANT_BIN"
  fi
  success "Qdrant siap"
fi

# Ollama (opsional)
echo ""
echo -n "Install Ollama untuk local LLM (gratis, privat)? [y/N] "
read -r WANT_OLLAMA
if [[ "$WANT_OLLAMA" =~ ^[Yy]$ ]]; then
  curl -fsSL https://ollama.ai/install.sh | sh
  info "Download model llama3.2:3b (2.0GB)..."
  ollama pull llama3.2:3b
  success "Ollama + llama3.2:3b siap"
fi

# Start Redis
if [[ "$OS" == "debian" || "$OS" == "fedora" ]]; then
  sudo systemctl enable redis-server --now 2>/dev/null || \
  sudo systemctl enable redis --now 2>/dev/null || true
elif [[ "$OS" == "macos" ]]; then
  brew services start redis 2>/dev/null || true
fi

# ── STEP 5: Config wizard ────────────────────────────────────
step "5/7 Konfigurasi SayAi"

CONFIG_FILE="$SAYAI_CONFIG/settings.yaml"
ENV_FILE="$SAYAI_CONFIG/.env"

if [[ ! -f "$CONFIG_FILE" ]]; then
  cat > "$CONFIG_FILE" << YAML
sayai:
  version: "1.0.0"
  mode: $MODE

llm:
  default_provider: anthropic
  default_model: claude-haiku-4-5-20251001
  routing:
    planning:  claude-sonnet-4-20250514
    coding:    openrouter/deepseek/deepseek-coder-v2
    searching: groq/llama-3.3-70b-versatile
    testing:   openrouter/deepseek/deepseek-coder-v2
    default:   claude-haiku-4-5-20251001
  fallback:
    - groq/llama-3.3-70b-versatile
    - ollama/llama3.2

memory:
  short_term_tokens: 8000
  vector_store: qdrant
  qdrant_url: http://localhost:6333

skillhunter:
  enabled: true
  schedule: "0 2 * * *"
  min_score: 0.6
  sources:
    - type: github
      query: "mcp server tool agent"
    - type: pypi
      tags: [ai, agent, mcp, tool]
    - type: mcp_registry
      url: https://registry.mcp.dev

admin:
  require_approval: true
  notify_tui: true

agents:
  max_parallel: 4
  max_iterations: 10
YAML

  # API keys
  echo ""
  echo -e "${BOLD}Masukkan API keys (kosongkan untuk skip):${N}"
  echo -n "  Anthropic API key  : "; read -rs K1; echo
  echo -n "  OpenRouter API key : "; read -rs K2; echo
  echo -n "  Groq API key       : "; read -rs K3; echo
  echo -n "  Gemini API key     : "; read -rs K4; echo

  {
    [[ -n "$K1" ]] && echo "ANTHROPIC_API_KEY=$K1"
    [[ -n "$K2" ]] && echo "OPENROUTER_API_KEY=$K2"
    [[ -n "$K3" ]] && echo "GROQ_API_KEY=$K3"
    [[ -n "$K4" ]] && echo "GEMINI_API_KEY=$K4"
  } > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  success "Config tersimpan"
fi

# ── STEP 6: VPS — systemd service ───────────────────────────
if [[ "$MODE" == "vps" ]]; then
  step "6/7 Setup systemd service"
  sudo tee /etc/systemd/system/sayai.service > /dev/null << SERVICE
[Unit]
Description=SayAi Agent Platform
After=network.target redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$SAYAI_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$SAYAI_DIR/.venv/bin/sayai server
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE
  sudo systemctl daemon-reload
  sudo systemctl enable sayai
  success "systemd service terdaftar. Start: sudo systemctl start sayai"
else
  step "6/7 Skip systemd (mode: $MODE)"
fi

# ── STEP 7: Init DB & PATH ───────────────────────────────────
step "7/7 Inisialisasi database & PATH"

"$SAYAI_DIR/.venv/bin/sayai" db init
success "Database terinisialisasi"

# Add to PATH
SHELL_RC=""
[[ "$SHELL" == *zsh*  ]] && SHELL_RC="$HOME/.zshrc"
[[ "$SHELL" == *bash* ]] && SHELL_RC="$HOME/.bashrc"

if [[ -n "$SHELL_RC" ]] && ! grep -q "sayai" "$SHELL_RC" 2>/dev/null; then
  echo "" >> "$SHELL_RC"
  echo "# SayAi" >> "$SHELL_RC"
  echo "export PATH=\"$SAYAI_DIR/.venv/bin:\$PATH\"" >> "$SHELL_RC"
fi

# ── Done! ────────────────────────────────────────────────────
echo ""
echo -e "${G}${BOLD}╔══════════════════════════════════════════╗${N}"
echo -e "${G}${BOLD}║   SayAi berhasil diinstall!              ║${N}"
echo -e "${G}${BOLD}╚══════════════════════════════════════════╝${N}"
echo ""
echo -e "  TUI interface : ${BOLD}sayai tui${N}"
echo -e "  Cari skill    : ${BOLD}sayai hunt${N}"
echo -e "  Admin panel   : ${BOLD}sayai admin${N}"
echo -e "  Bantuan       : ${BOLD}sayai --help${N}"
[[ "$MODE" == "vps" ]] && \
echo -e "  Start daemon  : ${BOLD}sudo systemctl start sayai${N}"
echo ""
echo -e "  Docs: ${B}https://sayai.dev/docs${N}"
echo -e "  Reload shell  : ${BOLD}source ~/.bashrc${N} (atau buka terminal baru)"
echo ""
```

---

## 15. Struktur Folder Lengkap

```
sayai/
├── pyproject.toml                  # definisi project, deps, scripts
├── README.md
├── install.sh                      # OneClick installer
├── .env.example                    # template env vars
│
├── sayai/                          # package utama
│   ├── __init__.py
│   ├── main.py                     # entry point CLI
│   │
│   ├── cli/                        # CLI & TUI
│   │   ├── app.py                  # Textual TUI app
│   │   ├── commands.py             # /command handlers
│   │   ├── admin.py                # admin review panel
│   │   └── components/             # Textual widgets
│   │       ├── chat.py
│   │       ├── sidebar.py
│   │       └── proposal_card.py
│   │
│   ├── orchestrator/               # Orchestrator layer
│   │   ├── orchestrator.py         # main orchestrator class
│   │   ├── planner.py              # LLM-powered task decomposer
│   │   ├── dag.py                  # DAG executor
│   │   ├── router.py               # task → agent router
│   │   └── aggregator.py           # result merger
│   │
│   ├── agents/                     # Agent pool
│   │   ├── base.py                 # BaseAgent ABC
│   │   ├── coder.py                # CoderAgent
│   │   ├── reviewer.py             # ReviewerAgent
│   │   ├── searcher.py             # SearcherAgent
│   │   ├── tester.py               # TesterAgent
│   │   └── planner_agent.py        # PlannerAgent (sub-planning)
│   │
│   ├── memory/                     # Memory system
│   │   ├── context.py              # short-term (sliding window)
│   │   ├── vector.py               # long-term (Qdrant)
│   │   ├── scratchpad.py           # working memory (Redis)
│   │   └── indexer.py              # otomatis index file ke vector
│   │
│   ├── tools/                      # Tool layer
│   │   ├── executor.py             # tool call parser & runner
│   │   ├── bash.py                 # bash execution (sandboxed)
│   │   ├── filesystem.py           # read/write/patch/list
│   │   ├── git.py                  # git diff/commit/log
│   │   ├── browser.py              # web fetch/search
│   │   ├── lsp.py                  # Language Server Protocol
│   │   ├── linter.py               # ruff, eslint, dll.
│   │   └── mcp_bridge.py           # MCP protocol bridge
│   │
│   ├── llm/                        # LLM Client layer
│   │   ├── client.py               # Custom LLMClient
│   │   ├── router.py               # SmartRouter
│   │   ├── hooks.py                # middleware hooks
│   │   ├── cache.py                # response caching
│   │   └── providers/              # custom provider overrides
│   │       ├── anthropic.py
│   │       └── ollama.py
│   │
│   ├── skillhunter/                # SkillHunter subsystem
│   │   ├── hunter.py               # main hunt orchestrator
│   │   ├── analyzer.py             # AI analyzer
│   │   ├── rewriter.py             # AI rewriter → SKILL.md
│   │   ├── proposal.py             # proposal generator
│   │   ├── notifier.py             # notifikasi admin
│   │   └── crawlers/
│   │       ├── base.py
│   │       ├── github.py
│   │       ├── pypi.py
│   │       ├── npm.py
│   │       ├── mcp_registry.py
│   │       └── rss.py
│   │
│   ├── db/                         # Database layer
│   │   ├── database.py             # SQLite connection
│   │   ├── models.py               # Pydantic models
│   │   ├── migrations/             # SQL migration files
│   │   └── skill_store.py          # Skill CRUD operations
│   │
│   ├── skills/                     # Built-in skills
│   │   ├── coding/
│   │   │   ├── python.md
│   │   │   ├── typescript.md
│   │   │   └── rust.md
│   │   ├── tools/
│   │   │   ├── git.md
│   │   │   ├── docker.md
│   │   │   └── bash.md
│   │   └── research/
│   │       ├── web_search.md
│   │       └── docs_reader.md
│   │
│   └── config/                     # Konfigurasi
│       ├── settings.py             # Pydantic settings model
│       └── defaults.yaml           # nilai default
│
├── tests/                          # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── docs/                           # Dokumentasi
    ├── architecture.md
    ├── skills.md
    ├── providers.md
    └── contributing.md
```

---

## 16. Tech Stack

| Komponen         | Teknologi                              | Alasan                                       |
|------------------|----------------------------------------|----------------------------------------------|
| Language         | Python 3.12+                           | Ekosistem AI terlengkap, asyncio mature      |
| TUI              | Textual + Rich                         | TUI React-like, beautiful out of the box     |
| CLI args         | Click                                  | Simple, pythonic                             |
| Async            | asyncio + anyio                        | Native Python async, anyio untuk compat      |
| Package mgr      | uv                                     | 10x lebih cepat dari pip, modern             |
| LLM abstraction  | LiteLLM                                | 100+ provider dengan satu interface          |
| LLM custom layer | Custom LLMClient (di atas LiteLLM)    | Routing, fallback, hooks                     |
| Vector DB        | Qdrant                                 | Open source, cepat, self-hostable            |
| Cache / working  | Redis                                  | Fast in-memory, pub/sub untuk agent comms    |
| Database         | SQLite (aiosqlite)                     | Zero-config, embedded, cukup untuk skala ini |
| Validation       | Pydantic v2                            | Type-safe config dan data models             |
| HTTP client      | httpx                                  | Async-first, modern requests replacement     |
| Testing          | pytest + pytest-asyncio + pytest-cov   |                                              |
| Linting          | ruff                                   | Sangat cepat, pengganti flake8+black         |
| Type check       | mypy                                   |                                              |

---

## 17. Konfigurasi (settings.yaml)

```yaml
# ~/.config/sayai/settings.yaml
# Konfigurasi lengkap SayAi

sayai:
  version: "1.0.0"
  mode: local               # local | vps | dev
  log_level: INFO

llm:
  default_provider: anthropic
  default_model: claude-haiku-4-5-20251001

  # Routing: task type → model
  routing:
    planning:   claude-sonnet-4-20250514
    coding:     openrouter/deepseek/deepseek-coder-v2
    reviewing:  claude-sonnet-4-20250514
    searching:  groq/llama-3.3-70b-versatile
    testing:    openrouter/deepseek/deepseek-coder-v2
    cheap:      groq/llama-3.3-70b-versatile
    default:    claude-haiku-4-5-20251001

  # Fallback chains
  fallback_chains:
    claude-sonnet-4-20250514:
      - gemini/gemini-2.5-pro
      - groq/llama-3.3-70b-versatile
    openrouter/deepseek/deepseek-coder-v2:
      - groq/llama-3.3-70b-versatile
      - claude-haiku-4-5-20251001

  # Provider configs
  providers:
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
    openrouter:
      api_key: ${OPENROUTER_API_KEY}
      base_url: https://openrouter.ai/api/v1
    groq:
      api_key: ${GROQ_API_KEY}
    gemini:
      api_key: ${GEMINI_API_KEY}
    ollama:
      base_url: http://localhost:11434

agents:
  max_parallel: 4           # berapa agent berjalan bersamaan
  max_iterations: 10        # max ReAct loop per agent
  timeout_seconds: 120      # timeout per task

memory:
  short_term_tokens: 8000
  vector_store: qdrant
  qdrant_url: http://localhost:6333
  qdrant_collection: sayai_memory
  redis_url: redis://localhost:6379

tools:
  bash_timeout: 30          # detik
  bash_max_output: 5000     # karakter
  allowed_dirs:             # direktori yang boleh ditulis
    - ${HOME}/projects
    - /tmp/sayai

skillhunter:
  enabled: true
  schedule: "0 2 * * *"    # setiap hari jam 02:00
  min_score: 0.6
  max_proposals_per_run: 10
  sources:
    - type: github
      enabled: true
      query: "mcp server tool agent"
    - type: pypi
      enabled: true
      tags: [ai, agent, mcp, tool]
    - type: mcp_registry
      enabled: true
      url: https://registry.mcp.dev
    - type: rss
      enabled: false
      feeds:
        - https://huggingface.co/papers.rss

admin:
  require_approval: true    # false = auto-approve (tidak disarankan)
  notify_tui: true
  notify_webhook: ""        # URL webhook Slack/Discord (opsional)
  notify_email: ""          # email admin (opsional)
```

---

## 18. Roadmap Pengembangan

### Phase 1 — Foundation 
- [ ] Setup project structure + pyproject.toml
- [ ] Implementasi LLMClient + SmartRouter + LiteLLM integration
- [ ] CoderAgent basic (read/write/bash)
- [ ] TUI sederhana dengan Textual
- [ ] Database SQLite + schema
- [ ] install.sh basic (local mode)

### Phase 2 — Orchestrator 
- [ ] Planner (LLM task decomposition)
- [ ] DAG Executor (asyncio.gather + dependency resolution)
- [ ] ReviewerAgent + TesterAgent
- [ ] SearcherAgent (web search + RAG dasar)
- [ ] Short-term memory (ContextManager)
- [ ] Fallback chain implementation

### Phase 3 — Memory & Tools 
- [ ] Long-term memory (Qdrant integration)
- [ ] Working memory (Redis scratchpad)
- [ ] Auto-indexing codebase ke vector store
- [ ] Tool layer lengkap (bash, fs, git, browser, linter)
- [ ] MCP Bridge
- [ ] LSP integration

### Phase 4 — SkillHunter 
- [ ] Crawler: GitHub, PyPI, MCP Registry
- [ ] AI Analyzer (relevance + license + safety)
- [ ] AI Rewriter (→ SKILL.md format)
- [ ] Admin Review Panel di TUI
- [ ] Notifikasi system
- [ ] Skill Store CRUD + versioning

### Phase 5 — Production
- [ ] install.sh complete (semua mode)
- [ ] VPS mode + systemd service
- [ ] Reflection & self-correction loop
- [ ] Cost tracking + dashboard
- [ ] Session sharing (share links)
- [ ] Plugin system (user extensions)
- [ ] Dokumentasi lengkap
- [ ] Test coverage > 80%

---

## 19. Prompt Library — Semua System Prompt

### 19.1 Planner System Prompt

```
Kamu adalah AI Planner untuk SayAi — platform agentic coding.
Tugasmu: menerima task kompleks dari user, lalu memecahnya menjadi
subtask yang spesifik, actionable, dan dapat dikerjakan secara paralel
atau berurutan oleh agent-agent spesialis.

OUTPUT: JSON array saja. Tidak ada teks lain, tidak ada markdown fence.

Format setiap task:
{
  "id": "task_A",
  "agent_type": "coder|reviewer|searcher|tester|planner",
  "instruction": "instruksi spesifik dan lengkap untuk agent",
  "depends_on": ["task_id_yang_harus_selesai_dulu"],
  "priority": 1,
  "budget": "cheap|normal|premium",
  "context_needed": ["file atau info yang perlu dibaca agent"]
}

Aturan decomposisi:
1. Parallelkan task yang tidak bergantung satu sama lain
2. tester selalu depends_on coder yang relevan
3. reviewer dapat berjalan paralel dengan tester
4. Gunakan searcher jika task butuh research atau dokumentasi luar
5. budget "cheap" (Groq) untuk task sederhana/cepat
6. budget "normal" (DeepSeek/Haiku) untuk coding standar
7. budget "premium" (Claude Sonnet) untuk planning/review kompleks
8. Jika task sangat kompleks, tambahkan planner_agent sebagai sub-planner
9. instruction harus cukup detail sehingga agent bisa bekerja mandiri
10. Minimal 2 task, maksimal 12 task per plan

Contoh output untuk "buat auth module dengan JWT":
[
  {
    "id": "search_jwt",
    "agent_type": "searcher",
    "instruction": "Cari library JWT terbaik untuk Python 2024. Bandingkan python-jose, PyJWT, dan authlib. Return: nama library yang direkomendasikan beserta alasannya.",
    "depends_on": [],
    "priority": 1,
    "budget": "cheap"
  },
  {
    "id": "code_auth",
    "agent_type": "coder",
    "instruction": "Tulis auth module di src/auth.py menggunakan library JWT hasil research. Implementasi: login(), logout(), verify_token(), refresh_token(). Gunakan konvensi kode yang sudah ada di project.",
    "depends_on": ["search_jwt"],
    "priority": 1,
    "budget": "normal"
  },
  {
    "id": "test_auth",
    "agent_type": "tester",
    "instruction": "Tulis unit tests untuk src/auth.py di tests/test_auth.py. Cover: happy path, invalid token, expired token, refresh flow. Jalankan tests dan pastikan semua pass.",
    "depends_on": ["code_auth"],
    "priority": 2,
    "budget": "normal"
  },
  {
    "id": "review_auth",
    "agent_type": "reviewer",
    "instruction": "Review src/auth.py untuk: keamanan (injection, timing attack, brute force), kualitas kode (DRY, SOLID), dan dokumentasi. Return: daftar issue dengan severity.",
    "depends_on": ["code_auth"],
    "priority": 2,
    "budget": "premium"
  }
]
```

### 19.2 CoderAgent System Prompt

```
Kamu adalah CoderAgent dari SayAi — expert software engineer dengan
pengalaman luas di Python, TypeScript, Rust, Go, dan bahasa lainnya.

Prinsip kerjamu:
1. Selalu baca file yang relevan sebelum menulis kode
2. Ikuti konvensi dan gaya kode yang sudah ada di project
3. Buat perubahan minimal yang diperlukan — jangan over-engineer
4. Tulis kode yang bisa dibaca manusia, bukan hanya mesin
5. Tambahkan docstring dan komentar pada logika yang kompleks
6. Jika tidak yakin, baca lebih banyak konteks sebelum menulis

Tools yang tersedia (gunakan dengan format XML):

<tool>read_file</tool><args>{"path": "relative/path/file.py"}</args>
<tool>write_file</tool><args>{"path": "path/file.py", "content": "isi file"}</args>
<tool>patch_file</tool><args>{"path": "path/file.py", "diff": "unified diff"}</args>
<tool>bash</tool><args>{"command": "command yang dijalankan"}</args>
<tool>list_dir</tool><args>{"path": "."}</args>
<tool>search_code</tool><args>{"query": "teks yang dicari", "path": "."}</args>
<tool>git_diff</tool><args>{}</args>

Alur kerja standar:
1. Baca task dengan seksama
2. Eksplorasi codebase yang relevan (list_dir, read_file, search_code)
3. Pahami konvensi dan pattern yang digunakan
4. Tulis atau modifikasi kode
5. Verifikasi dengan bash (syntax check, import test)
6. Laporkan apa yang telah dilakukan

Jika menemukan bug atau masalah lain saat bekerja, catat tapi jangan
perbaiki kecuali memang diminta. Fokus pada task yang diberikan.
```

### 19.3 ReviewerAgent System Prompt

```
Kamu adalah ReviewerAgent dari SayAi — code reviewer senior yang kritis
tapi konstruktif. Spesialisasimu: keamanan, kualitas kode, dan arsitektur.

Dimensi review:

KEAMANAN (prioritas tertinggi):
- Injection vulnerabilities (SQL, command, path traversal)
- Authentication & authorization flaws
- Hardcoded secrets atau credentials
- Insecure dependencies
- Race conditions dan concurrency issues
- Input validation yang lemah

KUALITAS KODE:
- DRY (Don't Repeat Yourself)
- Single Responsibility Principle
- Complexity yang berlebihan (cognitive complexity)
- Error handling yang tidak tepat
- Memory leaks
- Performa yang buruk (N+1 query, dll.)

MAINTAINABILITY:
- Dokumentasi dan docstring
- Naming yang jelas dan konsisten
- Test coverage
- Dead code

Tools:
<tool>read_file</tool><args>{"path": "path"}</args>
<tool>bash</tool><args>{"command": "ruff check path/ atau eslint path"}</args>
<tool>search_code</tool><args>{"query": "pattern"}</args>

Output format:
## Review: [nama file/komponen]

### CRITICAL (harus diperbaiki sebelum merge)
- [issue]: [penjelasan] — [baris/fungsi yang terdampak]

### WARNING (sebaiknya diperbaiki)
- [issue]: [penjelasan]

### SUGGESTION (opsional, nice to have)
- [saran]: [penjelasan]

### SUMMARY
[ringkasan singkat — apakah kode layak merge atau perlu revisi]
```

### 19.4 SearcherAgent System Prompt

```
Kamu adalah SearcherAgent dari SayAi — research specialist yang
efisien dan akurat. Tugasmu: mencari, mengumpulkan, dan mensintesis
informasi yang dibutuhkan agent lain.

Kemampuanmu:
- Web search untuk informasi terkini
- Fetch dan baca dokumentasi resmi
- Cari di codebase lokal
- Sintesis informasi dari berbagai sumber

Tools:
<tool>web_search</tool><args>{"query": "query pencarian"}</args>
<tool>fetch_url</tool><args>{"url": "https://..."}</args>
<tool>search_code</tool><args>{"query": "teks", "path": "."}</args>
<tool>read_file</tool><args>{"path": "path"}</args>

Aturan:
1. Verifikasi informasi dari minimal 2 sumber jika memungkinkan
2. Selalu cantumkan sumber URL untuk informasi penting
3. Prefer dokumentasi resmi daripada blog/forum
4. Jika informasi bertentangan, jelaskan perbedaannya
5. Ringkas temuan secara jelas untuk dikonsumsi agent lain
6. Tandai informasi yang mungkin sudah outdated

Output format:
## Research: [topik]

### Temuan Utama
[poin-poin utama yang ditemukan]

### Rekomendasi
[rekomendasi spesifik untuk task yang sedang dikerjakan]

### Sumber
- [sumber 1]: [URL]
- [sumber 2]: [URL]
```

### 19.5 TesterAgent System Prompt

```
Kamu adalah TesterAgent dari SayAi — QA engineer yang obsesif dengan
kualitas dan coverage. Tugasmu: memastikan kode bekerja dengan benar
melalui test yang komprehensif.

Strategi testing:
1. Unit tests untuk setiap fungsi/method publik
2. Integration tests untuk alur yang melibatkan beberapa komponen
3. Edge cases: null, empty, boundary values, error conditions
4. Happy path + semua unhappy path yang bermakna

Tools:
<tool>read_file</tool><args>{"path": "path"}</args>
<tool>write_file</tool><args>{"path": "path", "content": "content"}</args>
<tool>bash</tool><args>{"command": "pytest tests/ -v --cov"}</args>
<tool>search_code</tool><args>{"query": "pattern"}</args>

Framework yang digunakan (sesuaikan dengan project):
- Python: pytest + pytest-asyncio
- TypeScript: Jest / Vitest
- Rust: built-in #[test]

Aturan:
1. Baca implementasi sebelum menulis test
2. Test harus independent (tidak bergantung urutan)
3. Gunakan mock untuk external dependencies
4. Nama test harus deskriptif: test_fungsi_kondisi_expected_result
5. Jalankan test setelah ditulis, pastikan semua pass
6. Laporkan coverage yang dicapai

Jika test gagal:
1. Analisis failure message
2. Cek apakah bug di kode atau di test
3. Jika bug di kode, laporkan ke orchestrator (jangan perbaiki sendiri)
4. Jika bug di test, perbaiki test
```

### 19.6 SkillHunter Analyzer Prompt

```
Kamu adalah AI analyzer untuk SkillHunter — sistem pencari skill
otomatis milik SayAi. Tugasmu: mengevaluasi apakah sebuah library,
tool, atau MCP server layak dijadikan skill SayAi.

INPUT yang akan kamu terima:
- Nama dan versi library/tool
- URL sumber (GitHub, PyPI, npm, dll.)
- Deskripsi singkat
- README (sebagian)
- Lisensi yang ditemukan

OUTPUT: JSON saja, tidak ada teks lain.

Format output:
{
  "score": 0.0-1.0,
  "license": "MIT|Apache-2.0|GPL-3.0|proprietary|unknown",
  "copyright": "nama penulis dan tahun jika ditemukan",
  "is_duplicate": false,
  "safety_ok": true,
  "tags": ["tag1", "tag2"],
  "summary": "satu kalimat deskripsi apa yang dilakukan tool ini",
  "rejection_reason": null,
  "recommended": true
}

Kriteria scoring (0.0–1.0):
+0.3 jika langsung berguna untuk coding agent (bash, fs, git, browser, dll.)
+0.2 jika mendukung MCP protocol
+0.2 jika dokumentasi lengkap dan jelas
+0.1 jika aktif diperbarui (commit < 6 bulan)
+0.1 jika populer (> 100 stars di GitHub)
+0.1 jika dependency minimal
-0.3 jika lisensi tidak jelas atau restrictif
-0.2 jika dokumentasi sangat minim
-0.1 jika tidak ada tests

Tolak otomatis (score = 0, recommended = false) jika:
- Lisensi proprietary atau tidak ditemukan
- Konten berbahaya atau malicious
- Duplikat dari skill yang sudah ada
- Sangat irrelevan untuk coding agent

Selalu cantumkan copyright jika bisa ditemukan di README atau LICENSE file.
```

### 19.7 SkillHunter Rewriter Prompt

```
Kamu adalah AI rewriter untuk SkillHunter — tugasmu mengonversi
informasi tentang sebuah library/tool menjadi SKILL.md standar SayAi.

SKILL.md adalah dokumen instruksi yang dibaca oleh AI agent SayAi
untuk memahami kapan dan bagaimana menggunakan sebuah skill/tool.

Format SKILL.md yang harus kamu hasilkan:

---
name: [nama-skill-lowercase-hyphen]
version: [versi]
source: [URL sumber asli]
license: [lisensi]
copyright: "[copyright info]"
score: [score]
tags: [array tag]
---

# [Judul Skill]

[Satu paragraf deskripsi: apa yang dilakukan skill ini dan mengapa berguna
untuk AI coding agent]

## Kapan digunakan (triggers)

Gunakan skill ini ketika:
- [kondisi 1]
- [kondisi 2]
- [kondisi 3]

## Tools yang tersedia

- `nama_fungsi(param)` — penjelasan singkat
- `nama_fungsi2(param)` — penjelasan singkat

## Contoh penggunaan

```python
# Contoh kode nyata
```

## Instalasi (jika diperlukan)

```bash
# command install
```

## Dependensi

- [dependency 1]
- [dependency 2]

## Catatan copyright

[Cantumkan: skill ini diadaptasi dari [nama], oleh [author].
Lisensi asli: [lisensi]. Copyright [tahun] [penulis].
Semua perubahan dilisensikan di bawah MIT.]

---

Aturan penulisan:
1. Gunakan bahasa yang jelas dan langsung — ini dibaca oleh AI, bukan manusia
2. Triggers harus spesifik dan actionable
3. Contoh kode harus nyata dan bisa langsung dipakai
4. Selalu cantumkan copyright dengan benar
5. Jangan menambahkan informasi yang tidak ada di sumber asli
6. Output HANYA isi SKILL.md — tidak ada teks lain
```

---

## 20. Contoh Kode Implementasi

### pyproject.toml

```toml
[project]
name = "sayai"
version = "1.0.0"
description = "AI Agentic Coding Platform — multi-agent, orchestrator, SkillHunter"
requires-python = ">=3.12"
license = {text = "MIT"}

dependencies = [
    "litellm>=1.40.0",
    "textual>=0.61.0",
    "rich>=13.7.0",
    "click>=8.1.7",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "anyio>=4.4.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
    "qdrant-client>=1.9.0",
    "redis>=5.0.4",
    "python-dotenv>=1.0.1",
    "pyyaml>=6.0.1",
    "aiofiles>=23.2.1",
    "tiktoken>=0.7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.7",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.7",
    "mypy>=1.10.0",
]

[project.scripts]
sayai = "sayai.main:cli"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### main.py — CLI Entry Point

```python
# sayai/main.py
import click
import asyncio

@click.group()
@click.version_option("1.0.0")
def cli():
    """SayAi — AI Agentic Coding Platform"""
    pass

@cli.command()
def tui():
    """Buka TUI interface"""
    from sayai.cli.app import SayAiApp
    app = SayAiApp()
    app.run()

@cli.command()
def hunt():
    """Jalankan SkillHunter untuk mencari skill baru"""
    from sayai.skillhunter.hunter import SkillHunter
    from sayai.config import load_config
    config = load_config()
    hunter = SkillHunter(config.skillhunter)
    asyncio.run(hunter.hunt())

@cli.command()
def admin():
    """Buka admin panel untuk review skill proposals"""
    from sayai.cli.admin import AdminApp
    app = AdminApp()
    app.run()

@cli.group()
def db():
    """Database management"""
    pass

@db.command("init")
def db_init():
    """Inisialisasi database SayAi"""
    from sayai.db.database import init_db
    asyncio.run(init_db())
    click.echo("Database berhasil diinisialisasi.")

@cli.command()
@click.argument("task")
@click.option("--model", "-m", help="Override model yang digunakan")
def run(task: str, model: str):
    """Jalankan task langsung dari command line (non-interactive)"""
    from sayai.orchestrator import Orchestrator
    orchestrator = Orchestrator()

    async def _run():
        result = await orchestrator.run(task, model_override=model)
        click.echo(result)

    asyncio.run(_run())

if __name__ == "__main__":
    cli()
```

---

## Penutup

SayAi dirancang dari awal untuk menjadi platform coding agent yang benar-benar **self-evolving** — semakin dipakai, semakin pintar karena SkillHunter terus menambah kemampuan baru secara otomatis. Namun tetap **aman** karena setiap skill baru membutuhkan persetujuan admin.

Tiga keunggulan utama dibanding kompetitor:

1. **Multi-agent paralel dengan DAG** — task kompleks diselesaikan lebih cepat karena agent bekerja bersamaan
2. **SkillHunter** — tidak ada platform coding agent lain yang punya kemampuan ini
3. **OneClick installer** — dari zero ke running dalam satu command, support local maupun VPS

**Repository target:** `https://github.com/sayai-dev/sayai`  
**Dokumentasi:** `https://sayai.dev/docs`  
**Lisensi:** MIT

---

*Dokumen ini dibuat sebagai blueprint pengembangan SayAi v1.0.0*  
*Last updated: April 2026*
