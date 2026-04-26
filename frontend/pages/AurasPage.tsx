import { useConfig } from "../contexts/ConfigContext";
import ToggleSwitch from "../components/ToggleSwitch";

export default function AurasPage() {
    const { config, saveConfig, error } = useConfig();

    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    return (
        <>
            <div className="page-header">
                <h2>Auras</h2>
                <p>Aura detection, recording, and notification settings</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">✨</div>
                    <div>
                        <h3>Aura Detection</h3>
                        <p>Detect and notify about rare auras</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable Aura Detection"
                    description="Detect aura rolls and send webhook notifications"
                    checked={config.enable_aura_detection || false}
                    onChange={(val) => updateConfig("enable_aura_detection", val)}
                />

                {config.enable_aura_detection && (
                    <>
                        <ToggleSwitch
                            label="Aura Detection Screenshot"
                            description="Take a screenshot when you rolled a new aura (Only works if Roblox is focused/Fishing mode is OFF!)"
                            checked={config.aura_detection_screenshot || false}
                            onChange={(val) => updateConfig("aura_detection_screenshot", val)}
                        />

                        <div className="form-row" style={{ marginTop: "10px" }}>
                            <div className="form-group">
                                <label className="form-label">Ping Minimum Rarity</label>
                                <input
                                    className="form-input"
                                    value={config.ping_minimum || "100000"}
                                    onChange={(e) => updateConfig("ping_minimum", e.target.value)}
                                    style={{ width: "140px" }}
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Discord User ID</label>
                                <input
                                    className="form-input"
                                    value={config.aura_user_id || ""}
                                    onChange={(e) => updateConfig("aura_user_id", e.target.value)}
                                    placeholder="123456789012345678"
                                    style={{ width: "220px" }}
                                />
                            </div>
                        </div>

                        <div className="form-group" style={{ marginTop: "10px" }}>
                            <label className="form-label">Force Ping Auras</label>
                            <input
                                className="form-input"
                                value={config.force_ping_auras || ""}
                                onChange={(e) => updateConfig("force_ping_auras", e.target.value)}
                                placeholder="e.g. Oblivion, Illusionary,... (comma-separated)"
                                style={{ width: "100%" }}
                            />
                            <small style={{ color: "var(--text-muted)", fontSize: "12px", marginTop: "4px", display: "block" }}>
                                Pings Discord User ID even if rarity is not met. (otherwise don't put the auras in the box if you don't want the macro to force ping)
                            </small>
                        </div>
                    </>
                )}
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🎬</div>
                    <div>
                        <h3>Aura Recording</h3>
                        <p>Auto-clip when a rare aura is rolled</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable Aura Recording"
                    description="Trigger a recording keybind on rare aura rolls"
                    checked={config.enable_aura_record || false}
                    onChange={(val) => updateConfig("enable_aura_record", val)}
                />

                {config.enable_aura_record && (
                    <>
                        <div className="form-row" style={{ marginTop: "10px" }}>
                            <div className="form-group">
                                <label className="form-label">Record Keybind</label>
                                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                                    <input
                                        className="form-input"
                                        value={config.aura_record_keybind || "F8"}
                                        onChange={(e) => updateConfig("aura_record_keybind", e.target.value)}
                                        style={{ width: "100px" }}
                                    />
                                    <button
                                        className="btn btn-accent"
                                        onClick={() => {
                                            if ((window as any).pywebview) {
                                                (window as any).pywebview.api.test_aura_keybind();
                                            }
                                        }}
                                        style={{ padding: "8px 16px", whiteSpace: "nowrap" }}
                                    >
                                        Test Keybind
                                    </button>
                                    <small style={{ color: "var(--text-muted)", fontSize: "11px", whiteSpace: "nowrap" }}>
                                        (Fires after 2s delay)
                                    </small>
                                </div>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Min Rarity to Record</label>
                                <input
                                    className="form-input"
                                    value={config.aura_record_minimum || "100000"}
                                    onChange={(e) => updateConfig("aura_record_minimum", e.target.value)}
                                    style={{ width: "140px" }}
                                />
                            </div>
                        </div>

                        <div className="form-group" style={{ marginTop: "10px" }}>
                            <label className="form-label">Force Record Auras</label>
                            <input
                                className="form-input"
                                value={config.force_record_auras || ""}
                                onChange={(e) => updateConfig("force_record_auras", e.target.value)}
                                placeholder="e.g. Oblivion, Illusionary,... (comma-separated)"
                                style={{ width: "100%" }}
                            />
                            <small style={{ color: "var(--text-muted)", fontSize: "12px", marginTop: "4px", display: "block" }}>
                                Force aura record even if rarity is not met (otherwise don't put the auras in the box if you don't want the macro to force record)
                            </small>
                        </div>
                    </>
                )}
            </div>
        </>
    );
}
