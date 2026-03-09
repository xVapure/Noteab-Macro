import { useConfig } from "../contexts/ConfigContext";
import ToggleSwitch from "../components/ToggleSwitch";

export default function MovementsPage() {
    const { config, saveConfig, error } = useConfig();

    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    return (
        <>
            <div className="page-header">
                <h2>Movements</h2>
                <p>Automated movement and pathing configurations</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🗺️</div>
                    <div>
                        <h3>Basic Obby</h3>
                    </div>
                </div>

                <div style={{ marginBottom: "20px", padding: "10px", borderBottom: "1px solid var(--border-color)" }}>
                    <h4 style={{ margin: "0 0 10px 0" }}>Recorder</h4>
                    <button
                        className="btn"
                        onClick={() => { if (window.pywebview?.api) window.pywebview.api.open_recorder_window() }}
                        style={{ position: "relative", padding: "10px 20px" }}
                    >
                        <div className="corner-bracket tl" style={{ top: 0, left: 0, width: "6px", height: "6px" }} />
                        <div className="corner-bracket tr" style={{ top: 0, right: 0, width: "6px", height: "6px" }} />
                        <div className="corner-bracket bl" style={{ bottom: 0, left: 0, width: "6px", height: "6px" }} />
                        <div className="corner-bracket br" style={{ bottom: 0, right: 0, width: "6px", height: "6px" }} />
                        🔴 Record Obby Path
                    </button>
                </div>

                <div>
                    <ToggleSwitch
                        label="Auto complete Basic Obby"
                        checked={config.enable_auto_obby || false}
                        onChange={(val) => updateConfig("enable_auto_obby", val)}
                    />

                    {config.enable_auto_obby && (
                        <div className="form-group" style={{ marginTop: "15px", marginLeft: "10px" }}>
                            <label className="form-label">Interval (min):</label>
                            <input
                                className="form-input"
                                type="number"
                                value={config.auto_obby_interval || "15"}
                                onChange={(e) => updateConfig("auto_obby_interval", e.target.value)}
                                style={{ width: "80px" }}
                            />
                        </div>
                    )}

                    <div style={{ marginTop: "15px", borderTop: "1px solid var(--border-color)", paddingTop: "15px" }}>
                        <ToggleSwitch
                            label="Use aura that can float on water"
                            checked={config.use_float_aura || false}
                            onChange={(val) => updateConfig("use_float_aura", val)}
                        />

                        {config.use_float_aura && (
                            <div className="form-group" style={{ marginTop: "10px", marginLeft: "10px" }}>
                                <label className="form-label">Aura Name:</label>
                                <input
                                    className="form-input"
                                    type="text"
                                    value={config.float_aura_name || ""}
                                    onChange={(e) => updateConfig("float_aura_name", e.target.value)}
                                    placeholder="e.g. Sailor"
                                    style={{ width: "200px" }}
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
}
