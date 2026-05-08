import { useConfig } from "../contexts/ConfigContext";
import ToggleSwitch from "../components/ToggleSwitch";

export default function OtherFeaturesPage() {
    const { config, saveConfig, error } = useConfig();

    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    return (
        <>
            <div className="page-header">
                <h2>Other Features</h2>
                <p>Additional macro capabilities and experimental options</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">⚡</div>
                    <div>
                        <h3>Rare Biome Actions</h3>
                        <p>Actions to take when a rare biome is detected</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable buff when Glitched/Dreamspace"
                    description="ONLY use this feature when you have your buffs DISABLED while hunting for Glitched/Dreamspace"
                    checked={config.enable_buff_glitched || false}
                    onChange={(val) => updateConfig("enable_buff_glitched", val)}
                />

                <ToggleSwitch
                    label="Reset character when there's a rare biome"
                    description="Reset character to Sol's Main Island during GLITCHED/DREAMSPACE/CYBERSPACE"
                    checked={config.reset_on_rare || false}
                    onChange={(val) => updateConfig("reset_on_rare", val)}
                />

                <ToggleSwitch
                    label="Teleport back to Limbo when rare biome ends"
                    description="Return to limbo automatically when rare biome ended"
                    checked={config.teleport_back_to_limbo || false}
                    onChange={(val) => updateConfig("teleport_back_to_limbo", val)}
                />
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🛠️</div>
                    <div>
                        <h3>System Settings</h3>
                        <p>Application-wide preferences</p>
                    </div>
                </div>

                <div className="setting-row" style={{ padding: '15px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <div style={{ fontWeight: 600, color: 'var(--text-bright)' }}>Open AppData Folder</div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Opens the folder where logs, config, and macro data are stored</div>
                    </div>
                    <button 
                        className="btn primary" 
                        onClick={() => window.pywebview?.api?.open_appdata()}
                        style={{ padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', backgroundColor: 'var(--primary)', color: 'white', border: 'none', fontWeight: 600 }}
                    >
                        Open Folder
                    </button>
                </div>

                <ToggleSwitch
                    label="GLITCHED visual effect on macro UI when GLITCHED biome is found (to look cool ofc)"
                    description={<span style={{ color: "red", fontWeight: "bold" }}>ONLY USE THIS IF YOU ARE NON PHOTOSENSITIVE</span>}
                    checked={config.enable_glitch_effect || false}
                    onChange={(val) => updateConfig("enable_glitch_effect", val)}
                />

                <ToggleSwitch
                    label="Anti-AFK"
                    description="Prevents Roblox disconnection even when Roblox isn't focused"
                    checked={config.anti_afk || false}
                    onChange={(val) => updateConfig("anti_afk", val)}
                />

                <div className="setting-row" style={{ padding: '0 20px 20px 20px', display: 'flex', alignItems: 'center', gap: '15px' }}>
                    <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Usage Duration (minutes):</span>
                    <input 
                        type="number" 
                        className="form-input" 
                        style={{ width: '80px', textAlign: 'center' }}
                        value={config.anti_afk_interval || "5"}
                        min="1"
                        max="20"
                        onChange={(e) => updateConfig("anti_afk_interval", e.target.value)}
                    />
                </div>

                <ToggleSwitch
                    label="Auto Update (startup)"
                    description="Automatically download the latest macro update when the app opens"
                    checked={config.auto_update_enabled !== false}
                    onChange={(val) => updateConfig("auto_update_enabled", val)}
                />

                <ToggleSwitch
                    label="Enable Idle Mode"
                    description="Disable all automated actions except biome/aura detection and anti-afk."
                    checked={config.enable_idle_mode || false}
                    onChange={(val) => updateConfig("enable_idle_mode", val)}
                />

                <ToggleSwitch
                    label="Make Roblox instance on fullscreen"
                    description="Automatically fullscreen Roblox window when macro starts"
                    checked={config.auto_roblox_fullscreen || false}
                    onChange={(val) => updateConfig("auto_roblox_fullscreen", val)}
                />

                <ToggleSwitch
                    label="AZERTY Keyboard Mode (experimental)"
                    description="Enable this if you currently using AZERTY keyboard layout :aga:"
                    checked={config.azerty_mode || false}
                    onChange={(val) => updateConfig("azerty_mode", val)}
                />
            </div>
        </>
    );
}
