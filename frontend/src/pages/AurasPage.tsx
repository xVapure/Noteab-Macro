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

                        <ToggleSwitch
                            label="Aura Detection Screenshot"
                            description="Take a screenshot when you rolled a new aura (Only works if Roblox is focused/Fishing mode is OFF!)"
                            checked={config.aura_detection_screenshot || false}
                            onChange={(val) => updateConfig("aura_detection_screenshot", val)}
                        />
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
                    <div className="form-row" style={{ marginTop: "10px" }}>
                        <div className="form-group">
                            <label className="form-label">Record Keybind</label>
                            <input
                                className="form-input"
                                value={config.aura_record_keybind || "F8"}
                                onChange={(e) => updateConfig("aura_record_keybind", e.target.value)}
                                style={{ width: "140px" }}
                            />
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
                )}
            </div>
        </>
    );
}
