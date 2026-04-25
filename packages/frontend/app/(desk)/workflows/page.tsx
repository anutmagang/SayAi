"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";

import { apiFetch } from "@/lib/api";

function toWorkflowDefinition(nodes: Node[], edges: Edge[]) {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: String(n.data?.wfType || "wfInput"),
      position: n.position,
      data: { ...(n.data || {}) },
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
    })),
  };
}

const starterNodes: Node[] = [
  {
    id: "in1",
    type: "default",
    position: { x: 0, y: 0 },
    data: { label: "wfInput", wfType: "wfInput", required: ["topic"] },
  },
  {
    id: "llm1",
    type: "default",
    position: { x: 260, y: 0 },
    data: {
      label: "wfLlm",
      wfType: "wfLlm",
      model: "gpt-4o-mini",
      prompt: "Write one sentence about {topic}.",
      output_key: "summary",
    },
  },
  {
    id: "out1",
    type: "default",
    position: { x: 520, y: 0 },
    data: { label: "wfOutput", wfType: "wfOutput", pick: "summary", name: "result" },
  },
];

const starterEdges: Edge[] = [
  { id: "e1", source: "in1", target: "llm1" },
  { id: "e2", source: "llm1", target: "out1" },
];

export default function WorkflowsPage() {
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [name, setName] = useState("My workflow");
  const [topic, setTopic] = useState("vector databases");
  const [log, setLog] = useState<string>("");

  const [nodes, setNodes, onNodesChange] = useNodesState(starterNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(starterEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  const definition = useMemo(() => toWorkflowDefinition(nodes, edges), [nodes, edges]);

  async function save() {
    setLog("");
    if (!workflowId) {
      const r = await apiFetch("/api/v1/workflows", {
        method: "POST",
        body: JSON.stringify({ name, definition }),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        setLog(JSON.stringify(body, null, 2));
        return;
      }
      setWorkflowId(body.id);
      setLog(`Created workflow ${body.id}`);
      return;
    }

    const r = await apiFetch(`/api/v1/workflows/${workflowId}`, {
      method: "PUT",
      body: JSON.stringify({ name, definition }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      setLog(JSON.stringify(body, null, 2));
      return;
    }
    setLog(`Saved workflow ${workflowId}`);
  }

  async function run() {
    setLog("");
    if (!workflowId) {
      setLog("Save first to create a workflow id.");
      return;
    }
    const r = await apiFetch(`/api/v1/workflows/${workflowId}/runs`, {
      method: "POST",
      body: JSON.stringify({ inputs: { topic }, await_completion: true }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      setLog(JSON.stringify(body, null, 2));
      return;
    }
    setLog(JSON.stringify(body, null, 2));
  }

  return (
    <main className="flex h-screen flex-col">
      <header className="flex items-center justify-between gap-3 border-b border-slate-800 px-4 py-3">
        <div className="flex items-center gap-3">
          <Link className="text-sky-300 underline" href="/">
            Home
          </Link>
          <span className="text-sm text-slate-300">React Flow → API</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            className="w-56 rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Workflow name"
          />
          <input
            className="w-56 rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-sm"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="inputs.topic"
          />
          <button
            className="rounded-md bg-slate-800 px-3 py-1 text-sm hover:bg-slate-700"
            type="button"
            onClick={save}
          >
            Save definition
          </button>
          <button
            className="rounded-md bg-sky-600 px-3 py-1 text-sm font-medium hover:bg-sky-500"
            type="button"
            onClick={run}
          >
            Run (await)
          </button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_420px]">
        <div className="min-h-0">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
          >
            <MiniMap />
            <Controls />
            <Background gap={16} />
          </ReactFlow>
        </div>
        <aside className="border-t border-slate-800 p-4 text-sm text-slate-200 lg:border-l lg:border-t-0">
          <p className="mb-2 font-medium">Notes</p>
          <ul className="list-disc space-y-2 pl-5 text-slate-300">
            <li>Nodes use <code className="text-slate-100">data.wfType</code> for export.</li>
            <li>
              Edge connects <code className="text-slate-100">wfInput → wfLlm → wfOutput</code>.
            </li>
            <li>Streaming: open a WS client to `/api/v1/workflow-runs/&lt;id&gt;/stream`.</li>
          </ul>
          <pre className="mt-4 max-h-[45vh] overflow-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
            {log || "Run output appears here."}
          </pre>
        </aside>
      </div>
    </main>
  );
}
