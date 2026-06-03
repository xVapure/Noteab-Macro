import { useEffect, useState, useRef } from "react";
import { useConfig } from "../contexts/ConfigContext";

interface ModuleStatus {
    active: boolean;
    enabled: boolean;
}

interface ActiveModulesResponse {
    modules: Record<string, ModuleStatus>;
    incompatibilities: string[];
}

export default function StatusPage() {
    const { isMacroRunning } = useConfig();
    const [statusData, setStatusData] = useState<ActiveModulesResponse | null>(null);
    const [logLines, setLogLines] = useState<string[]>([]);
    const [autoScroll, setAutoScroll] = useState(true);
    const [modulePage, setModulePage] = useState(0);
    const [moduleFilter, setModuleFilter] = useState<"all" | "active" | "idle" | "disabled">("all");
    const logContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        let isMounted = true;
        
        const fetchStatus = async () => {
            if (!window.pywebview?.api?.get_active_modules) return;
            try {
                const data = await window.pywebview.api.get_active_modules();
                if (isMounted) {
                    setStatusData(data);
                }
            } catch (err) {
                console.error("Failed to fetch active modules:", err);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 2000);

        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, []);

    useEffect(() => {
        let isMounted = true;

        const fetchLogs = async () => {
            if (!window.pywebview?.api?.get_macro_logs) return;
            try {
                const data = await window.pywebview.api.get_macro_logs();
                if (isMounted && data?.lines) {
                    setLogLines(data.lines);
                }
            } catch (err) {
                console.error("Failed to fetch macro logs:", err);
            }
        };

        fetchLogs();
        const logInterval = setInterval(fetchLogs, 3000);

        return () => {
            isMounted = false;
            clearInterval(logInterval);
        };
    }, []);

    useEffect(() => {
        if (autoScroll && logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
        }
    }, [logLines, autoScroll]);

    const handleLogScroll = () => {
        const el = logContainerRef.current;
        if (!el) return;
        const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
        setAutoScroll(nearBottom);
    };

    if (!statusData) {
        return <div style={{ padding: "20px" }}>Loading status information...</div>;
    }

    return (
        <>
            <div className="page-header">
                <h2>Macro Status</h2>
            </div>

            {statusData.incompatibilities.length > 0 && (
                <div className="card" style={{ borderLeft: "4px solid #ef4444", background: "rgba(239, 68, 68, 0.05)" }}>
                    <div className="card-header">
                        <div className="card-icon" style={{ color: "#ef4444" }}>⚠️</div>
                        <div>
                            <h3 style={{ color: "#ef4444" }}>Potential Issues Found!</h3>
                            <p>The following conflicts or settings might prevent some actions from running:</p>
                        </div>
                    </div>
                    <ul style={{ margin: "10px 0 0 20px", color: "#f87171", lineHeight: "1.6" }}>
                        {statusData.incompatibilities.map((item, idx) => (
                            <li key={idx}>{item}</li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">⚙️</div>
                    <div style={{ flex: 1 }}>
                        <h3>Macro Modules State</h3>
                        <p>u can check currently running or enabled macro actions state here btw</p>
                    </div>
                </div>

                {/* module filter */}
                <div style={{ display: "flex", gap: "6px", marginTop: "10px", flexWrap: "wrap" }}>
                    {([
                        { key: "all" as const, label: "All", color: "var(--text-bright)", dotColor: "" },
                        { key: "active" as const, label: "Active", color: "#22c55e", dotColor: "#22c55e" },
                        { key: "idle" as const, label: "Idle", color: "#f59e0b", dotColor: "#f59e0b" },
                        { key: "disabled" as const, label: "Disabled", color: "#6b7280", dotColor: "#6b7280" },
                    ]).map(f => {
                        const isActive = moduleFilter === f.key;
                        return (
                            <button
                                key={f.key}
                                onClick={() => { setModuleFilter(f.key); setModulePage(0); }}
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "5px",
                                    padding: "5px 12px",
                                    fontSize: "0.85rem",
                                    fontFamily: "inherit",
                                    fontWeight: 600,
                                    borderRadius: "4px",
                                    cursor: "pointer",
                                    border: `1px solid ${isActive ? f.color : "var(--border)"}`,
                                    background: isActive ? `${f.dotColor || "var(--text-bright)"}15` : "rgba(255,255,255,0.03)",
                                    color: isActive ? f.color : "var(--text-muted)",
                                    transition: "all 0.15s ease",
                                }}
                            >
                                {f.dotColor && <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: f.dotColor, flexShrink: 0 }} />}
                                {f.label}
                            </button>
                        );
                    })}
                </div>

                {(() => {
                    const MODULES_PER_PAGE = 8;
                    const allEntries = Object.entries(statusData.modules);
                    const filtered = allEntries.filter(([, s]) => {
                        if (moduleFilter === "all") return true;
                        if (moduleFilter === "active") return s.active;
                        if (moduleFilter === "idle") return s.enabled && !s.active;
                        return !s.enabled;
                    });
                    const totalPages = Math.max(1, Math.ceil(filtered.length / MODULES_PER_PAGE));
                    const safePage = Math.min(modulePage, totalPages - 1);
                    const pageEntries = filtered.slice(safePage * MODULES_PER_PAGE, (safePage + 1) * MODULES_PER_PAGE);

                    return (
                        <>
                            {filtered.length === 0 ? (
                                <div style={{ padding: "16px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.82rem", opacity: 0.6 }}>
                                    No modules match this filter.
                                </div>
                            ) : (
                                <div style={{
                                    display: "grid",
                                    gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                                    gap: "8px",
                                    marginTop: "8px",
                                }}>
                                    {pageEntries.map(([name, status]) => (
                                        <div key={name} style={{
                                            padding: "8px 12px",
                                            background: "rgba(255,255,255,0.03)",
                                            border: "1px solid var(--border)",
                                            borderRadius: "5px",
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "space-between",
                                            opacity: status.enabled ? 1 : 0.45,
                                            minHeight: "36px",
                                        }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                                <div style={{
                                                    width: "8px",
                                                    height: "8px",
                                                    borderRadius: "50%",
                                                    background: status.active ? "#22c55e" : (status.enabled ? "#f59e0b" : "#6b7280"),
                                                    boxShadow: status.active ? "0 0 6px #22c55e" : "none",
                                                    flexShrink: 0,
                                                }} />
                                                <span style={{ fontSize: "0.9rem", fontWeight: 600, color: status.active ? "var(--text-bright)" : "var(--text-muted)" }}>{name}</span>
                                            </div>
                                            <span style={{
                                                fontSize: "0.8rem",
                                                textTransform: "uppercase",
                                                fontWeight: 700,
                                                letterSpacing: "0.4px",
                                                color: status.active ? "#22c55e" : (status.enabled ? "#f59e0b" : "#6b7280"),
                                            }}>
                                                {status.active ? "Active" : (status.enabled ? "Idle" : "Off")}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {totalPages > 1 && (
                                <div style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    gap: "12px",
                                    marginTop: "10px",
                                }}>
                                    <button
                                        onClick={() => setModulePage(p => Math.max(0, p - 1))}
                                        disabled={safePage === 0}
                                        style={{
                                            background: "rgba(255,255,255,0.06)",
                                            border: "1px solid var(--border)",
                                            color: safePage === 0 ? "var(--text-muted)" : "var(--text-bright)",
                                            borderRadius: "4px",
                                            padding: "4px 12px",
                                            fontSize: "0.85rem",
                                            fontFamily: "inherit",
                                            cursor: safePage === 0 ? "not-allowed" : "pointer",
                                            opacity: safePage === 0 ? 0.4 : 1,
                                        }}
                                    >◀ Prev</button>
                                    <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                                        {safePage + 1} / {totalPages}
                                    </span>
                                    <button
                                        onClick={() => setModulePage(p => Math.min(totalPages - 1, p + 1))}
                                        disabled={safePage >= totalPages - 1}
                                        style={{
                                            background: "rgba(255,255,255,0.06)",
                                            border: "1px solid var(--border)",
                                            color: safePage >= totalPages - 1 ? "var(--text-muted)" : "var(--text-bright)",
                                            borderRadius: "4px",
                                            padding: "4px 12px",
                                            fontSize: "0.85rem",
                                            fontFamily: "inherit",
                                            cursor: safePage >= totalPages - 1 ? "not-allowed" : "pointer",
                                            opacity: safePage >= totalPages - 1 ? 0.4 : 1,
                                        }}
                                    >Next ▶</button>
                                </div>
                            )}
                        </>
                    );
                })()}
            </div>

            {/* Macro Log Viewer */}
            <div className="card">
                <div className="card-header">
                    <div className="card-icon">📋</div>
                    <div>
                        <h3>Macro Session Log</h3>
                    </div>
                </div>

                <div
                    ref={logContainerRef}
                    onScroll={handleLogScroll}
                    style={{
                        marginTop: "10px",
                        maxHeight: "320px",
                        overflowY: "auto",
                        background: "rgba(0, 0, 0, 0.35)",
                        border: "1px solid var(--border)",
                        borderRadius: "6px",
                        padding: "10px 14px",
                        fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
                        fontSize: "0.75rem",
                        lineHeight: "1.55",
                        color: "var(--text-muted)",
                        scrollbarWidth: "thin",
                    }}
                >
                    {logLines.length === 0 ? (
                        <div style={{ color: "var(--text-muted)", opacity: 0.5, fontStyle: "italic" }}>
                            No log entries yet — start the macro to see output here.
                        </div>
                    ) : (
                        logLines.map((line, idx) => {
                            let lineColor = "var(--text-muted)";
                            const lower = line.toLowerCase();
                            if (lower.includes("error") || lower.includes("failed")) {
                                lineColor = "#f87171";
                            } else if (lower.includes("warn")) {
                                lineColor = "#fbbf24";
                            } else if (lower.includes("[log]")) {
                                lineColor = "#94a3b8";
                            } else if (lower.includes("biome") || lower.includes("aura")) {
                                lineColor = "#67e8f9";
                            } else if (lower.includes("webhook") || lower.includes("sent")) {
                                lineColor = "#86efac";
                            }

                            return (
                                <div key={idx} style={{
                                    color: lineColor,
                                    padding: "1px 0",
                                    wordBreak: "break-all",
                                    borderBottom: "1px solid rgba(255,255,255,0.03)",
                                }}>
                                    {line}
                                </div>
                            );
                        })
                    )}
                </div>

                {!autoScroll && logLines.length > 0 && (
                    <div style={{ textAlign: "center", marginTop: "6px" }}>
                        <button
                            onClick={() => {
                                setAutoScroll(true);
                                if (logContainerRef.current) {
                                    logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
                                }
                            }}
                            style={{
                                background: "rgba(59, 130, 246, 0.15)",
                                border: "1px solid rgba(59, 130, 246, 0.3)",
                                color: "#60a5fa",
                                padding: "4px 14px",
                                borderRadius: "4px",
                                fontSize: "0.75rem",
                                cursor: "pointer",
                            }}
                        >
                            ↓ Scroll to bottom
                        </button>
                    </div>
                )}
            </div>

            {!isMacroRunning && (
                <div className="info-banner" style={{ marginTop: "16px" }}>
                    Macro is currently STOPPED. Most modules will appear as Idle or Disabled until you start the macro (F1).
                </div>
            )}
        </>
    );
}
