import { useEffect, useState } from "react";
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
                    <div>
                        <h3>Active Modules</h3>
                        <p>u can check currently running or enabled macro actions here btw</p>
                    </div>
                </div>

                <div className="status-grid" style={{ 
                    display: "grid", 
                    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", 
                    gap: "12px",
                    marginTop: "10px"
                }}>
                    {Object.entries(statusData.modules).map(([name, status]) => (
                        <div key={name} style={{
                            padding: "12px 16px",
                            background: "rgba(255,255,255,0.03)",
                            border: "1px solid var(--border)",
                            borderRadius: "6px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            opacity: status.enabled ? 1 : 0.5
                        }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                <div style={{ 
                                    width: "10px", 
                                    height: "10px", 
                                    borderRadius: "50%", 
                                    background: status.active ? "#22c55e" : (status.enabled ? "#f59e0b" : "#6b7280"),
                                    boxShadow: status.active ? "0 0 8px #22c55e" : "none"
                                }} />
                                <span style={{ fontWeight: 600, color: status.active ? "var(--text-bright)" : "var(--text-muted)" }}>{name}</span>
                            </div>
                            <div style={{ fontSize: "0.8rem", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.5px" }}>
                                {status.active ? (
                                    <span style={{ color: "#22c55e" }}>Active</span>
                                ) : (
                                    status.enabled ? <span style={{ color: "#f59e0b" }}>Paused/Idle</span> : <span style={{ color: "#6b7280" }}>Disabled</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
                
                <div style={{ marginTop: "20px", padding: "12px", background: "rgba(0,0,0,0.2)", borderRadius: "6px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    <div style={{ display: "flex", gap: "15px", flexWrap: "wrap" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#22c55e" }} />
                            <span>Currently Performing Action</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#f59e0b" }} />
                            <span>Enabled but currently Idle</span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#6b7280" }} />
                            <span>Disabled in Settings</span>
                        </div>
                    </div>
                </div>
            </div>

            {!isMacroRunning && (
                <div className="info-banner" style={{ marginTop: "16px" }}>
                    Macro is currently STOPPED. Most modules will appear as Idle or Disabled until you start the macro (F1).
                </div>
            )}
        </>
    );
}
