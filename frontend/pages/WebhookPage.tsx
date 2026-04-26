import { useState } from "react";
import { useConfig } from "../contexts/ConfigContext";
import { looksLikeWebhookUrl, getWebhookWarning } from "../utils/webhookGuard";

export default function WebhookPage() {
    const { config, saveConfig, error } = useConfig();
    const [testing, setTesting] = useState(false);
    const [visible, setVisible] = useState<Record<number, boolean>>({});

    if (error) return (
        <div style={{ padding: "20px", color: "#ef4444" }}>
            <h3>Error Loading Config</h3>
            <p>{error}</p>
        </div>
    );

    if (!config) return <div style={{ padding: "20px" }}>Loading config...</div>;

    const urls = (config.webhook_url && config.webhook_url.length > 0) ? config.webhook_url : [""];
    const biomes = config.biome_notifier || {};

    const updateUrls = (newUrls: string[]) => {
        saveConfig({ ...config, webhook_url: newUrls });
    };

    const addUrl = () => updateUrls([...urls, ""]);
    const removeUrl = (i: number) => {
        const newVisible = { ...visible };
        delete newVisible[i];
        setVisible(prev => {
            const next = { ...prev };
            delete next[i];
            return next;
        });
        updateUrls(urls.filter((_, idx) => idx !== i));
    };

    const updateUrl = (i: number, val: string) => {
        const next = [...urls];
        next[i] = val;
        updateUrls(next);
    };

    const toggleVisible = (i: number) => {
        setVisible(prev => ({ ...prev, [i]: !prev[i] }));
    };

    const updateBiomeSetting = (biome: string, value: string) => {
        const newNotifier = { ...biomes, [biome]: value };
        saveConfig({ ...config, biome_notifier: newNotifier });
    };

    const handleRobloxUsernameChange = (val: string) => {
        if (looksLikeWebhookUrl(val)) {
            alert(getWebhookWarning(val, "Roblox Username"));
            return;
        }
        saveConfig({ ...config, roblox_username: val });
    };

    const handlePrivateServerLinkChange = (val: string) => {
        if (looksLikeWebhookUrl(val)) {
            alert(getWebhookWarning(val, "Private Server Link"));
            return;
        }
        saveConfig({ ...config, private_server_link: val });
    };

    const handleTestWebhooks = async () => {
        if (testing) return;
        setTesting(true);
        try {
            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.send_webhook_status("Webhook Sent Successfully!", 5814783);
            }
        } catch (e) {
            alert("Failed to send test: " + e);
        } finally {
            setTesting(false);
        }
    };

    return (
        <>
            <div className="page-header">
                <h2>Webhook</h2>
                <p>Configure Discord webhook URLs for notifications</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">👤</div>
                    <div>
                        <h3>Your Roblox username</h3>
                        <p>input your Roblox username (case-insensitive) for higher logs accuracy reading</p>
                    </div>
                </div>
                <input
                    className="form-input"
                    placeholder="Enter your Roblox username"
                    style={{ width: "100%" }}
                    value={config.roblox_username || ""}
                    onChange={(e) => handleRobloxUsernameChange(e.target.value)}
                />
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🔗</div>
                    <div>
                        <h3>Discord Webhook URLs</h3>
                        <p>Multiple webhook URLs are supported!</p>
                    </div>
                </div>

                <div className="webhook-list">
                    {urls.map((url, i) => (
                        <div key={i} className="webhook-entry">
                            <button
                                className="btn-icon"
                                onClick={() => toggleVisible(i)}
                                style={{
                                    marginRight: "8px",
                                    background: "rgba(255,255,255,0.1)",
                                    border: "none",
                                    borderRadius: "4px",
                                    width: "32px",
                                    height: "32px",
                                    cursor: "pointer",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center"
                                }}
                                title={visible[i] ? "Hide URL" : "Show URL"}
                            >
                                {visible[i] ? "👁️" : "🔒"}
                            </button>
                            <input
                                type={visible[i] ? "text" : "password"}
                                className="form-input"
                                placeholder={`Webhook URL ${i + 1}`}
                                value={url}
                                onChange={(e) => updateUrl(i, e.target.value)}
                            />
                            <button className="btn-remove" onClick={() => removeUrl(i)}>
                                ×
                            </button>
                        </div>
                    ))}
                </div>

                <div style={{ display: "flex", gap: "8px" }}>
                    <button className="btn btn-secondary" onClick={addUrl}>
                        + Add URL
                    </button>
                    <button
                        className="btn btn-accent"
                        onClick={handleTestWebhooks}
                        disabled={testing}
                        style={{ opacity: testing ? 0.7 : 1 }}
                    >
                        {testing ? "Sending..." : "Test Webhooks"}
                    </button>
                </div>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🔗</div>
                    <div>
                        <h3>Private Server Link</h3>
                        <p>Your Roblox private server link when there's rare biomes</p>
                    </div>
                </div>
                <input
                    className="form-input"
                    placeholder="https://www.roblox.com/games/..."
                    style={{ width: "100%" }}
                    value={config.private_server_link || ""}
                    onChange={(e) => handlePrivateServerLinkChange(e.target.value)}
                />
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">⚙️</div>
                    <div>
                        <h3>Biome Configuration</h3>
                        <p>Configure notifications for specific biomes</p>
                    </div>
                </div>

                <div style={{
                    color: "#ef4444",
                    fontSize: "13px",
                    marginBottom: "16px",
                    textAlign: "center",
                    fontWeight: 600
                }}>
                    GLITCHED, DREAMSPACE & CYBERSPACE are both forced 'everyone' ping grrr &gt;:((
                </div>

                <div className="settings-grid">
                    {[
                        "WINDY", "RAINY", "SNOWY", "SAND STORM",
                        "HELL", "STARFALL", "CORRUPTION", "NULL",
                        "AURORA", "HEAVEN"
                    ].map(biome => (
                        <div key={biome} className="setting-row">
                            <span className="setting-label" style={{
                                color: ({
                                    "WINDY": "#9ae5ff",
                                    "RAINY": "#027cbd",
                                    "SNOWY": "#Dceff9",
                                    "SAND STORM": "#8F7057",
                                    "HELL": "#ff4719",
                                    "STARFALL": "#011ab7",
                                    "CORRUPTION": "#6d32a8",
                                    "NULL": "#838383",
                                    "AURORA": "#56d6a0",
                                    "HEAVEN": "#dfaf63"
                                } as Record<string, string>)[biome]
                            }}>{biome}:</span>
                            <select
                                className="form-input"
                                style={{ width: "140px" }}
                                value={biomes[biome] || "Message"}
                                onChange={(e) => updateBiomeSetting(biome, e.target.value)}
                            >
                                <option value="Message">Message</option>
                                <option value="None">None</option>
                            </select>
                        </div>
                    ))}
                </div>
            </div>
        </>
    );
}