import { useConfig } from "../contexts/ConfigContext";
import ToggleSwitch from "../components/ToggleSwitch";

export default function PathingPage() {
    const { config, saveConfig, error } = useConfig();

    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    return (
        <>
            <div className="page-header">
                <h2>Pathing</h2>
                <p>Configure movement paths for automated navigation</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">⛄</div>
                    <div>
                        <h3>Snowman Path</h3>
                        <p>Pre-configured snowflake collection routes</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable Snowman Path"
                    checked={config.enable_snowman_path || false}
                    onChange={(val) => updateConfig("enable_snowman_path", val)}
                />

                {config.enable_snowman_path && (
                    <div className="form-group" style={{ marginTop: "12px" }}>
                        <label className="form-label">Claim Interval (minutes)</label>
                        <input
                            className="form-input"
                            value={config.snowman_claim_interval || "15"}
                            onChange={(e) => updateConfig("snowman_claim_interval", e.target.value)}
                            style={{ width: "80px" }}
                        />
                    </div>
                )}
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🗺️</div>
                    <div>
                        <h3>Navigation Settings</h3>
                        <p>General pathing and reset behaviors</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Reset Character on Rare Biome"
                    description="Resets character to spawn/limbo when a rare biome is detected"
                    checked={config.reset_on_rare || false}
                    onChange={(val) => updateConfig("reset_on_rare", val)}
                />

                <ToggleSwitch
                    label="Teleport Back to Limbo"
                    description="Teleport back to the limbo area after efficient pathing"
                    checked={config.teleport_back_to_limbo || false}
                    onChange={(val) => updateConfig("teleport_back_to_limbo", val)}
                />
            </div>
        </>
    );
}
