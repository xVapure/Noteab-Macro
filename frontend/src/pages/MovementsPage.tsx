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
                    <div className="card-icon">⚙️</div>
                    <div>
                        <h3>General Pathing Settings</h3>
                    </div>
                </div>

                <ToggleSwitch
                    label="Non-VIP Movement Path"
                    description="Slow down to applied movement paths (basic obby, fishing, etc...) to compensate for non-VIP walkspeed"
                    checked={config.non_vip_movement_path || false}
                    onChange={(val) => updateConfig("non_vip_movement_path", val)}
                />

                <ToggleSwitch
                    label="Close Roblox chat before pathing (DO MACRO CALIBRATION - IMPORTANT)"
                    description="Automatically close the in-game chat using OCR detection before obby/fishing/events path sequences"
                    checked={config.auto_chat_close || false}
                    onChange={(val) => updateConfig("auto_chat_close", val)}
                />
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🗺️</div>
                    <div>
                        <h3>Basic Obby</h3>
                    </div>
                </div>

                <div>
                    <ToggleSwitch
                        label="Auto complete Basic Obby"
                        checked={config.enable_auto_obby || false}
                        onChange={async (val) => {
                            if (val) {
                                try {
                                    if (window.pywebview?.api) {
                                        const hasPath = await window.pywebview.api.check_obby_path_exists();
                                        if (!hasPath) {
                                            alert("No obby path found!\n\nPlease record an obby path first using the obby recorder above.");
                                            return;
                                        }
                                    }
                                } catch (e) {
                                    console.error("Failed to check obby path:", e);
                                }
                            }
                            updateConfig("enable_auto_obby", val);
                        }}
                    />

                    {config.enable_auto_obby && (
                        <div className="form-group" style={{ marginTop: "15px", marginLeft: "10px" }}>
                            <label className="form-label">Interval (min):</label>
                            <input
                                className="form-input"
                                type="number"
                                min="1"
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
