import { useState, useEffect, useRef } from "react";
import ToggleSwitch from "../components/ToggleSwitch";

export default function PotionCraftPage() {
    // State
    const [enableCrafting, setEnableCrafting] = useState(false);
    const [selectedPotion, setSelectedPotion] = useState("");
    const [potionFiles, setPotionFiles] = useState<string[]>([]);

    // Switching Logic
    const [enableSwitching, setEnableSwitching] = useState(false);
    const [switchInterval, setSwitchInterval] = useState(60);
    const [potion1, setPotion1] = useState("");
    const [potion2, setPotion2] = useState("");
    const [potion3, setPotion3] = useState("");
    const saveQueueRef = useRef<Promise<void>>(Promise.resolve());
    const configSnapshotRef = useRef<any>(null);

    useEffect(() => {
        refreshFiles();
        loadConfig();
    }, []);

    const refreshFiles = async () => {
        try {
            if (window.pywebview && window.pywebview.api) {
                const files = await window.pywebview.api.list_potion_files();
                setPotionFiles(files);
            }
        } catch (e) {
            console.error("Failed to list files:", e);
        }
    };

    const loadConfig = async () => {
        try {
            if (window.pywebview && window.pywebview.api) {
                const config: any = await window.pywebview.api.get_config();
                if (config) {
                    configSnapshotRef.current = config;
                    if (typeof config.enable_potion_crafting === 'boolean') setEnableCrafting(config.enable_potion_crafting);
                    setSelectedPotion(config.selected_potion_file ?? "");
                    if (typeof config.enable_potion_switching === 'boolean') setEnableSwitching(config.enable_potion_switching);
                    setSwitchInterval(Number(config.potion_switch_interval ?? 60));
                    setPotion1(config.potion_file_1 ?? "");
                    setPotion2(config.potion_file_2 ?? "");
                    setPotion3(config.potion_file_3 ?? "");
                }
            }
        } catch (e) {
            console.error("Failed to load config:", e);
        }
    };

    const saveConfig = (key: string, value: any) => {
        saveQueueRef.current = saveQueueRef.current
            .then(async () => {
                if (window.pywebview && window.pywebview.api) {
                    const baseConfig: any = configSnapshotRef.current ?? await window.pywebview.api.get_config();
                    const newConfig = { ...(baseConfig || {}), [key]: value };
                    configSnapshotRef.current = newConfig;
                    await window.pywebview.api.save_config(newConfig);
                }
            })
            .catch((e) => {
                console.error("Failed to save config:", e);
            });
    };

    // Generic handler to update state and save config
    const handleNumberChange = (val: string) => {
        const num = parseInt(val) || 0;
        setSwitchInterval(num);
        saveConfig("potion_switch_interval", num);
    };

    const openRecorder = async () => {
        try {
            if (window.pywebview?.api) {
                await window.pywebview.api.open_recorder_window_potion();
            }
        } catch (e) {
            console.error(e);
        }
    };

    // UI Helpers
    const PotionDropdown = ({ value, onChange, placeholder }: any) => (
        <div style={{ position: "relative", width: "100%" }}>
            <select
                className="form-input"
                style={{ width: "100%" }}
                value={value}
                onChange={(e) => onChange(e.target.value)}
            >
                <option value="">{placeholder}</option>
                {potionFiles.map(f => (
                    <option key={f} value={f}>{f}</option>
                ))}
            </select>
        </div>
    );

    return (
        <div className="animate-fade-in">
            <div className="page-header">
                <h2>Potion Crafting</h2>
                <p>Record and replay Stella's potion crafting sequences</p>
            </div>

            {/* Corner Borders container style similar to Obby */}
            <div style={{ position: "relative", border: "1px solid var(--border-color)", padding: "20px", marginBottom: "20px", background: "var(--card-bg)" }}>
                <div className="corner-bracket tl"></div>
                <div className="corner-bracket tr"></div>
                <div className="corner-bracket bl"></div>
                <div className="corner-bracket br"></div>

                <div className="card-header">
                    <div className="card-icon">🧪</div>
                    <div>
                        <h3>Auto Craft</h3>
                        <p>Automatically craft potions using recorded recipes</p>
                    </div>
                </div>

                <div style={{ marginBottom: "15px" }}>
                    <ToggleSwitch
                        label="Enable Auto Craft"
                        description="Run selected recipe on a loop when macro is running (THIS WILL CANCEL ALL OTHERS MACRO ACTIONS FOR POTION CRAFTING)"
                        checked={enableCrafting}
                        onChange={(v) => { setEnableCrafting(v); saveConfig("enable_potion_crafting", v); }}
                    />
                </div>

                <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "12px" }}>
                    <button className="btn btn-accent" onClick={openRecorder} style={{ fontSize: "12px", padding: "6px 12px" }}>
                        ⏺ Open Potion Recorder
                    </button>
                    <button className="btn" onClick={refreshFiles} style={{ fontSize: "12px", padding: "6px 12px", backgroundColor: "#374151", color: "white", border: "1px solid var(--border-color)" }}>
                        🔄 Refresh Files
                    </button>
                </div>

                <div className="form-group">
                    <label className="form-label">Selected Recipe</label>
                    <PotionDropdown
                        value={selectedPotion}
                        onChange={(v: string) => { setSelectedPotion(v); saveConfig("selected_potion_file", v); }}
                        placeholder="— Select a recipe file —"
                    />
                </div>
            </div>

            {/* Switching Section */}
            <div style={{ position: "relative", border: "1px solid var(--border-color)", padding: "20px", background: "var(--card-bg)" }}>
                <div className="corner-bracket tl"></div>
                <div className="corner-bracket tr"></div>
                <div className="corner-bracket bl"></div>
                <div className="corner-bracket br"></div>

                <div className="card-header">
                    <div className="card-icon">🔄</div>
                    <div>
                        <h3>Potion Switching</h3>
                        <p>Automatically switch between different potion recipes</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable potion switching"
                    description="Switch to next potion after interval"
                    checked={enableSwitching}
                    onChange={(v) => { setEnableSwitching(v); saveConfig("enable_potion_switching", v); }}
                />

                <div className="form-group" style={{ marginTop: "15px" }}>
                    <label className="form-label">Switch interval (seconds)</label>
                    <input
                        type="number"
                        className="form-input"
                        value={switchInterval}
                        onChange={(e) => handleNumberChange(e.target.value)}
                    />
                </div>

                <div className="form-group">
                    <label className="form-label">Select potion #1</label>
                    <PotionDropdown
                        value={potion1}
                        onChange={(v: string) => { setPotion1(v); saveConfig("potion_file_1", v); }}
                        placeholder="— None —"
                    />
                </div>

                <div className="form-group">
                    <label className="form-label">Select potion #2</label>
                    <PotionDropdown
                        value={potion2}
                        onChange={(v: string) => { setPotion2(v); saveConfig("potion_file_2", v); }}
                        placeholder="— None —"
                    />
                </div>

                <div className="form-group">
                    <label className="form-label">Select potion #3</label>
                    <PotionDropdown
                        value={potion3}
                        onChange={(v: string) => { setPotion3(v); saveConfig("potion_file_3", v); }}
                        placeholder="— None —"
                    />
                </div>

            </div>
        </div>
    );
}
