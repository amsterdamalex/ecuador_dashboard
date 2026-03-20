import React, { useState, useRef, useCallback, useEffect } from "react";

// ─── Agent Definitions ───────────────────────────────────────────────
const AGENTS = [
  {
    id: "analyst",
    name: "Analyst",
    icon: "⚗️",
    color: "#6366f1",
    bg: "#eef2ff",
    border: "#c7d2fe",
    prompt:
      "You are a meticulous analytical agent. Decompose the topic into definitions, mechanisms, and structural elements. Provide factual, structured insight cards.",
  },
  {
    id: "innovator",
    name: "Innovator",
    icon: "💡",
    color: "#f59e0b",
    bg: "#fffbeb",
    border: "#fde68a",
    prompt:
      "You are a creative innovator agent. Find surprising, unconventional, lateral, and futuristic angles on the topic. Provide creative and speculative insight cards.",
  },
  {
    id: "critic",
    name: "Devil's Advocate",
    icon: "⚡",
    color: "#ef4444",
    bg: "#fef2f2",
    border: "#fecaca",
    prompt:
      "You are a devil's advocate agent. Challenge assumptions, surface risks, counterarguments, and downsides of the topic. Provide critical, risk-focused insight cards.",
  },
  {
    id: "connector",
    name: "Connector",
    icon: "🔗",
    color: "#10b981",
    bg: "#ecfdf5",
    border: "#a7f3d0",
    prompt:
      "You are a cross-domain connector agent. Find unexpected links between the topic and other fields, disciplines, history, and culture. Provide cross-domain connection cards.",
  },
  {
    id: "questioner",
    name: "Questioner",
    icon: "◎",
    color: "#8b5cf6",
    bg: "#f5f3ff",
    border: "#ddd6fe",
    prompt:
      "You are a Socratic questioner agent. Generate thought-provoking questions that deepen understanding of the topic. Provide question cards that challenge the reader to think deeper.",
  },
];

// ─── Pentagon Geometry ───────────────────────────────────────────────
const RADIUS = 350;
const AGENT_ANGLES = [-90, -18, 54, 126, 198];
const CARD_W = 190;
const CARD_H = 122;
const CARD_GAP = 12;

function clusterCenter(index) {
  const angle = (AGENT_ANGLES[index] * Math.PI) / 180;
  return { x: Math.cos(angle) * RADIUS, y: Math.sin(angle) * RADIUS };
}

function cardPositions() {
  const offsets = [
    { r: 0, c: 0 },
    { r: 0, c: 1 },
    { r: 1, c: 0 },
    { r: 1, c: 1 },
  ];
  return offsets.map(({ r, c }) => ({
    dx: (c - 1) * (CARD_W + CARD_GAP) + CARD_GAP / 2,
    dy: r * (CARD_H + CARD_GAP) + 30,
  }));
}

// ─── Keyframes (injected once) ───────────────────────────────────────
const STYLE_TAG = `
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

@keyframes shimmer {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(220%); }
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes pulse {
  0%, 100% { opacity: 0.35; }
  50% { opacity: 1; }
}
@keyframes popIn {
  0% { transform: scale(0.82); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
@keyframes glow {
  0%, 100% { box-shadow: 0 0 24px rgba(99,102,241,0.25); }
  50% { box-shadow: 0 0 48px rgba(99,102,241,0.55); }
}
`;

// ─── API Call ─────────────────────────────────────────────────────────
async function callAgent(agent, topic) {
  const systemPrompt = `${agent.prompt}\n\nReturn ONLY a raw JSON array of exactly 4 objects.\nNo markdown fences, no preamble, no explanation — just the JSON array:\n[{"title":"short title","content":"2-3 sentence insight"},...]`;

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": "{{ANTHROPIC_API_KEY}}",
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 900,
      system: systemPrompt,
      messages: [{ role: "user", content: `Topic: ${topic}` }],
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      err?.error?.message || `API error ${res.status}: ${res.statusText}`
    );
  }

  const data = await res.json();
  const raw = data.content?.[0]?.text || "";
  const match = raw.match(/\[[\s\S]*\]/);
  if (!match) throw new Error("Agent returned invalid format — no JSON array found.");
  const parsed = JSON.parse(match[0]);
  if (!Array.isArray(parsed) || parsed.length < 1) throw new Error("Agent returned empty or invalid array.");
  return parsed.slice(0, 4);
}

// ─── Main Component ──────────────────────────────────────────────────
export default function Mirofish() {
  const [phase, setPhase] = useState("input");
  const [topicDraft, setTopicDraft] = useState("");
  const [topic, setTopic] = useState("");
  const [agentStatus, setAgentStatus] = useState(
    Object.fromEntries(AGENTS.map((a) => [a.id, "idle"]))
  );
  const [notes, setNotes] = useState([]);
  const [shown, setShown] = useState(new Set());
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [scale, setScale] = useState(0.68);

  const canvasRef = useRef(null);
  const dragging = useRef(false);
  const lastMouse = useRef({ x: 0, y: 0 });

  // ─── Inject styles ──────────────────────────────────────────────
  useEffect(() => {
    const id = "__mirofish_styles";
    if (!document.getElementById(id)) {
      const el = document.createElement("style");
      el.id = id;
      el.textContent = STYLE_TAG;
      document.head.appendChild(el);
    }
  }, []);

  // ─── Fire agents ────────────────────────────────────────────────
  const fireAgents = useCallback(
    (t) => {
      AGENTS.forEach((agent) => {
        setAgentStatus((prev) => ({ ...prev, [agent.id]: "thinking" }));
        callAgent(agent, t)
          .then((cards) => {
            setAgentStatus((prev) => ({ ...prev, [agent.id]: "done" }));
            const newNotes = cards.map((c, i) => ({
              id: `${agent.id}-${i}`,
              agentId: agent.id,
              title: c.title,
              content: c.content,
              index: i,
            }));
            setNotes((prev) => [...prev, ...newNotes]);
          })
          .catch((err) => {
            setAgentStatus((prev) => ({ ...prev, [agent.id]: "error" }));
            setNotes((prev) => [
              ...prev,
              {
                id: `${agent.id}-error`,
                agentId: agent.id,
                title: "Error",
                content: err.message,
                index: 0,
                isError: true,
              },
            ]);
          });
      });
    },
    []
  );

  // ─── Pop-in stagger ─────────────────────────────────────────────
  useEffect(() => {
    notes.forEach((note, i) => {
      if (!shown.has(note.id)) {
        setTimeout(() => {
          setShown((prev) => new Set(prev).add(note.id));
        }, note.index * 160);
      }
    });
  }, [notes, shown]);

  // ─── Handlers ───────────────────────────────────────────────────
  const handleStart = () => {
    const t = topicDraft.trim();
    if (!t) return;
    setTopic(t);
    setNotes([]);
    setShown(new Set());
    setAgentStatus(Object.fromEntries(AGENTS.map((a) => [a.id, "idle"])));
    setScale(0.68);
    setPan({ x: 0, y: 0 });
    setPhase("canvas");
    setTimeout(() => fireAgents(t), 100);
  };

  const handleNew = () => {
    setPhase("input");
    setTopicDraft("");
  };

  // ─── Pan / Zoom ─────────────────────────────────────────────────
  const onMouseDown = (e) => {
    if (e.target.closest("[data-interactive]")) return;
    dragging.current = true;
    lastMouse.current = { x: e.clientX, y: e.clientY };
  };
  const onMouseMove = (e) => {
    if (!dragging.current) return;
    const dx = e.clientX - lastMouse.current.x;
    const dy = e.clientY - lastMouse.current.y;
    lastMouse.current = { x: e.clientX, y: e.clientY };
    setPan((p) => ({ x: p.x + dx, y: p.y + dy }));
  };
  const onMouseUp = () => {
    dragging.current = false;
  };
  const onWheel = (e) => {
    e.preventDefault();
    setScale((s) => Math.min(3.0, Math.max(0.15, s - e.deltaY * 0.001)));
  };

  const zoomIn = () => setScale((s) => Math.min(3.0, s + 0.15));
  const zoomOut = () => setScale((s) => Math.max(0.15, s - 0.15));
  const resetView = () => {
    setScale(0.68);
    setPan({ x: 0, y: 0 });
  };

  // ─── Derived ────────────────────────────────────────────────────
  const doneCount = AGENTS.filter(
    (a) => agentStatus[a.id] === "done" || agentStatus[a.id] === "error"
  ).length;
  const isRunning = doneCount < 5 && phase === "canvas" && topic;
  const allDone = doneCount === 5 && phase === "canvas" && topic;
  const positions = cardPositions();

  // ─── Styles ─────────────────────────────────────────────────────
  const S = {
    root: {
      fontFamily: "'Syne', sans-serif",
      width: "100%",
      height: "100vh",
      background: "#0f0f13",
      color: "#e4e4e7",
      overflow: "hidden",
      position: "relative",
      userSelect: "none",
    },
    // Splash
    splash: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      height: "100%",
      gap: 28,
    },
    logo: {
      fontSize: 52,
      fontWeight: 800,
      background: "linear-gradient(135deg, #6366f1, #a78bfa, #f59e0b)",
      WebkitBackgroundClip: "text",
      WebkitTextFillColor: "transparent",
      letterSpacing: -1,
    },
    subtitle: {
      fontSize: 16,
      color: "#71717a",
      maxWidth: 440,
      textAlign: "center",
      lineHeight: 1.6,
    },
    inputRow: {
      display: "flex",
      gap: 10,
      width: "100%",
      maxWidth: 480,
    },
    input: {
      flex: 1,
      padding: "12px 18px",
      borderRadius: 12,
      border: "1.5px solid #27272a",
      background: "#18181b",
      color: "#e4e4e7",
      fontSize: 15,
      fontFamily: "'Syne', sans-serif",
      outline: "none",
    },
    btn: {
      padding: "12px 24px",
      borderRadius: 12,
      border: "none",
      background: "linear-gradient(135deg, #6366f1, #818cf8)",
      color: "#fff",
      fontWeight: 700,
      fontSize: 15,
      cursor: "pointer",
      fontFamily: "'Syne', sans-serif",
    },
    btnDisabled: {
      opacity: 0.4,
      cursor: "not-allowed",
    },
    suggestions: {
      display: "flex",
      gap: 8,
      flexWrap: "wrap",
      justifyContent: "center",
      maxWidth: 500,
    },
    chip: {
      padding: "6px 14px",
      borderRadius: 20,
      border: "1px solid #27272a",
      background: "#18181b",
      color: "#a1a1aa",
      fontSize: 13,
      cursor: "pointer",
      fontFamily: "'Syne', sans-serif",
    },
    // Top bar
    topBar: {
      position: "absolute",
      top: 0,
      left: 0,
      right: 0,
      height: 52,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 18px",
      background: "rgba(15,15,19,0.85)",
      backdropFilter: "blur(12px)",
      borderBottom: "1px solid #27272a",
      zIndex: 100,
    },
    topLeft: { display: "flex", alignItems: "center", gap: 12 },
    topRight: { display: "flex", alignItems: "center", gap: 8 },
    newBtn: {
      padding: "6px 14px",
      borderRadius: 8,
      border: "1px solid #27272a",
      background: "#18181b",
      color: "#a1a1aa",
      fontSize: 13,
      cursor: "pointer",
      fontFamily: "'Syne', sans-serif",
    },
    zoomBtn: {
      width: 32,
      height: 32,
      borderRadius: 8,
      border: "1px solid #27272a",
      background: "#18181b",
      color: "#a1a1aa",
      fontSize: 16,
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "'Syne', sans-serif",
    },
    progress: {
      fontSize: 13,
      fontFamily: "'JetBrains Mono', monospace",
      color: "#a1a1aa",
    },
    progressDone: {
      color: "#10b981",
    },
    // Bottom status bar
    statusBar: {
      position: "absolute",
      bottom: 0,
      left: 0,
      right: 0,
      height: 48,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 24,
      background: "rgba(15,15,19,0.85)",
      backdropFilter: "blur(12px)",
      borderTop: "1px solid #27272a",
      zIndex: 100,
    },
    statusAgent: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      fontSize: 12,
      fontFamily: "'JetBrains Mono', monospace",
    },
    // Canvas
    canvasOuter: {
      width: "100%",
      height: "100%",
      cursor: dragging.current ? "grabbing" : "grab",
      overflow: "hidden",
    },
  };

  // ─── Render: Splash ─────────────────────────────────────────────
  if (phase === "input") {
    const examples = [
      "Quantum Computing",
      "Future of Education",
      "CRISPR Gene Editing",
      "Web3 & Decentralization",
    ];
    const disabled = !topicDraft.trim();
    return (
      <div style={S.root}>
        <div style={S.splash}>
          <div style={S.logo}>mirofish</div>
          <div style={S.subtitle}>
            Enter any topic and five AI agents will analyse it simultaneously,
            placing their insights on an infinite canvas.
          </div>
          <div style={S.inputRow}>
            <input
              style={S.input}
              placeholder="Enter a topic to explore…"
              value={topicDraft}
              onChange={(e) => setTopicDraft(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !disabled && handleStart()}
              autoFocus
            />
            <button
              style={{ ...S.btn, ...(disabled ? S.btnDisabled : {}) }}
              onClick={handleStart}
              disabled={disabled}
            >
              Explore
            </button>
          </div>
          <div style={S.suggestions}>
            {examples.map((ex) => (
              <span
                key={ex}
                style={S.chip}
                onClick={() => {
                  setTopicDraft(ex);
                }}
              >
                {ex}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ─── Render: Canvas ─────────────────────────────────────────────
  return (
    <div style={S.root}>
      {/* Top bar */}
      <div style={S.topBar} data-interactive="true">
        <div style={S.topLeft}>
          <button style={S.newBtn} onClick={handleNew}>
            ← new
          </button>
          <span
            style={{
              fontSize: 15,
              fontWeight: 700,
              background: "linear-gradient(135deg, #6366f1, #a78bfa)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            mirofish
          </span>
        </div>
        <div style={S.topRight}>
          {isRunning ? (
            <span style={S.progress}>{doneCount}/5 agents</span>
          ) : allDone ? (
            <span style={{ ...S.progress, ...S.progressDone }}>✓ complete</span>
          ) : null}
          <button style={S.zoomBtn} onClick={zoomOut} data-interactive="true">
            −
          </button>
          <span
            style={{
              fontSize: 11,
              color: "#71717a",
              fontFamily: "'JetBrains Mono', monospace",
              minWidth: 40,
              textAlign: "center",
            }}
          >
            {Math.round(scale * 100)}%
          </span>
          <button style={S.zoomBtn} onClick={zoomIn} data-interactive="true">
            +
          </button>
          <button style={S.zoomBtn} onClick={resetView} data-interactive="true">
            ⌂
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div
        ref={canvasRef}
        style={S.canvasOuter}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onWheel={onWheel}
      >
        {/* Dot grid background */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage:
              "radial-gradient(circle, #27272a 1px, transparent 1px)",
            backgroundSize: `${24 * scale}px ${24 * scale}px`,
            backgroundPosition: `${pan.x}px ${pan.y}px`,
            pointerEvents: "none",
          }}
        />

        {/* World container */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`,
            transformOrigin: "0 0",
          }}
        >
          {/* Spoke lines */}
          {AGENTS.map((agent, i) => {
            const c = clusterCenter(i);
            return (
              <svg
                key={`spoke-${agent.id}`}
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  overflow: "visible",
                  pointerEvents: "none",
                }}
              >
                <line
                  x1={0}
                  y1={0}
                  x2={c.x}
                  y2={c.y}
                  stroke={agent.color}
                  strokeWidth={1.5}
                  strokeDasharray="6 4"
                  opacity={
                    agentStatus[agent.id] === "thinking"
                      ? 0.7
                      : agentStatus[agent.id] === "done"
                      ? 0.4
                      : 0.2
                  }
                />
              </svg>
            );
          })}

          {/* Topic node */}
          <div
            style={{
              position: "absolute",
              transform: "translate(-50%, -50%)",
              background: "linear-gradient(135deg, #1e1b4b, #312e81)",
              border: "2px solid #6366f1",
              borderRadius: 20,
              padding: "18px 32px",
              textAlign: "center",
              minWidth: 160,
              maxWidth: 280,
              animation: "glow 3s ease-in-out infinite",
              zIndex: 10,
            }}
          >
            <div
              style={{
                fontSize: 11,
                color: "#818cf8",
                textTransform: "uppercase",
                letterSpacing: 2,
                marginBottom: 6,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              topic
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, lineHeight: 1.3 }}>
              {topic}
            </div>
          </div>

          {/* Agent clusters */}
          {AGENTS.map((agent, agentIdx) => {
            const center = clusterCenter(agentIdx);
            const status = agentStatus[agent.id];
            const agentNotes = notes.filter((n) => n.agentId === agent.id);

            return (
              <div
                key={agent.id}
                style={{
                  position: "absolute",
                  left: center.x,
                  top: center.y,
                  transform: "translate(-50%, -50%)",
                }}
              >
                {/* Cluster header */}
                <div
                  style={{
                    textAlign: "center",
                    marginBottom: 8,
                    transform: "translateX(50%)",
                  }}
                >
                  <span style={{ fontSize: 18, marginRight: 6 }}>
                    {agent.icon}
                  </span>
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 700,
                      color: agent.color,
                    }}
                  >
                    {agent.name}
                  </span>
                  {status === "thinking" && (
                    <span
                      style={{
                        marginLeft: 8,
                        fontSize: 11,
                        color: "#71717a",
                        animation: "pulse 1.2s ease-in-out infinite",
                      }}
                    >
                      thinking…
                    </span>
                  )}
                  {status === "done" && (
                    <span
                      style={{
                        marginLeft: 8,
                        fontSize: 11,
                        color: "#10b981",
                      }}
                    >
                      ✓ done
                    </span>
                  )}
                  {status === "error" && (
                    <span
                      style={{
                        marginLeft: 8,
                        fontSize: 11,
                        color: "#ef4444",
                      }}
                    >
                      ✕ error
                    </span>
                  )}
                </div>

                {/* Cards grid */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: `${CARD_W}px ${CARD_W}px`,
                    gap: CARD_GAP,
                  }}
                >
                  {(status === "thinking" || status === "idle"
                    ? [0, 1, 2, 3]
                    : []
                  ).map((idx) => (
                    <div
                      key={`skel-${agent.id}-${idx}`}
                      style={{
                        width: CARD_W,
                        height: CARD_H,
                        borderRadius: 12,
                        background: "#1c1c22",
                        border: `1px solid #27272a`,
                        overflow: "hidden",
                        position: "relative",
                      }}
                    >
                      {/* Shimmer */}
                      <div
                        style={{
                          position: "absolute",
                          inset: 0,
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            position: "absolute",
                            top: 0,
                            left: 0,
                            width: "50%",
                            height: "100%",
                            background: `linear-gradient(90deg, transparent, ${agent.color}15, transparent)`,
                            animation: "shimmer 1.6s ease-in-out infinite",
                          }}
                        />
                      </div>
                      {/* Skeleton lines */}
                      <div style={{ padding: 14 }}>
                        <div
                          style={{
                            width: "60%",
                            height: 10,
                            borderRadius: 4,
                            background: "#27272a",
                            marginBottom: 12,
                          }}
                        />
                        <div
                          style={{
                            width: "90%",
                            height: 8,
                            borderRadius: 4,
                            background: "#27272a",
                            marginBottom: 8,
                          }}
                        />
                        <div
                          style={{
                            width: "75%",
                            height: 8,
                            borderRadius: 4,
                            background: "#27272a",
                          }}
                        />
                      </div>
                    </div>
                  ))}

                  {agentNotes.map((note) => (
                    <div
                      key={note.id}
                      style={{
                        width: CARD_W,
                        height: CARD_H,
                        borderRadius: 12,
                        background: note.isError ? "#2a1215" : agent.bg,
                        border: `1.5px solid ${
                          note.isError ? "#ef4444" : agent.border
                        }`,
                        padding: 14,
                        overflow: "hidden",
                        animation: shown.has(note.id)
                          ? "popIn 0.4s cubic-bezier(.34,1.56,.64,1) forwards"
                          : "none",
                        opacity: shown.has(note.id) ? 1 : 0,
                      }}
                    >
                      <div
                        style={{
                          fontSize: 12,
                          fontWeight: 700,
                          color: note.isError ? "#ef4444" : agent.color,
                          marginBottom: 8,
                          lineHeight: 1.3,
                        }}
                      >
                        {note.title}
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          color: note.isError ? "#fca5a5" : "#3f3f46",
                          lineHeight: 1.5,
                          fontFamily: "'JetBrains Mono', monospace",
                          display: "-webkit-box",
                          WebkitLineClamp: 4,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {note.content}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom status bar */}
      <div style={S.statusBar} data-interactive="true">
        {AGENTS.map((agent) => {
          const status = agentStatus[agent.id];
          return (
            <div key={agent.id} style={S.statusAgent}>
              {/* Status dot */}
              {status === "idle" && (
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: agent.color,
                    animation: "pulse 1.4s ease-in-out infinite",
                  }}
                />
              )}
              {status === "thinking" && (
                <div
                  style={{
                    width: 14,
                    height: 14,
                    borderRadius: "50%",
                    border: `2px solid ${agent.color}`,
                    borderTopColor: "transparent",
                    animation: "spin 0.85s linear infinite",
                  }}
                />
              )}
              {status === "done" && (
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: agent.color,
                  }}
                />
              )}
              {status === "error" && (
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "#ef4444",
                  }}
                />
              )}
              <span style={{ color: agent.color }}>{agent.icon}</span>
              <span style={{ color: "#71717a" }}>{agent.name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
