import { useConfig } from "../contexts/ConfigContext";
import ToggleSwitch from "../components/ToggleSwitch";

export default function RemoteAccessPage() {
    const { config, saveConfig, error } = useConfig();

    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    return (
        <>
            <div className="page-header">
                <h2>Remote Access</h2>
                <p>Control your macro remotely via a Discord bot</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🔑</div>
                    <div>
                        <h3>Remote Access Control</h3>
                        <p>Enable and configure remote macro control</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable Remote Access Control"
                    checked={config.remote_access_enabled || false}
                    onChange={(val) => updateConfig("remote_access_enabled", val)}
                />

                {config.remote_access_enabled && (
                    <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "12px" }}>
                        <div className="form-group">
                            <label className="form-label">Discord Bot Token:</label>
                            <input
                                className="form-input"
                                type="password"
                                value={config.remote_bot_token || ""}
                                onChange={(e) => updateConfig("remote_bot_token", e.target.value)}
                                placeholder="Enter your Discord bot token"
                                style={{ width: "100%", maxWidth: "440px" }}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Allowed User ID:</label>
                            <input
                                className="form-input"
                                value={config.remote_allowed_user_id || ""}
                                onChange={(e) => updateConfig("remote_allowed_user_id", e.target.value)}
                                placeholder="123456789012345678"
                                style={{ width: "220px" }}
                            />
                        </div>

                        <div>
                            <a
                                href="https://www.youtube.com/watch?v=s2S7Bncx9ns"
                                target="_blank"
                                rel="noreferrer"
                                style={{
                                    color: "royalblue",
                                    textDecoration: "underline",
                                    cursor: "pointer",
                                    fontSize: "13px",
                                }}
                            >
                                Setup tutorial
                            </a>
                        </div>
                    </div>
                )}
            </div>
        </>
    );
}
