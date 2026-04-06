import { useState, useEffect } from "react";
import { useConfig } from "../contexts/ConfigContext";
import ToggleSwitch from "../components/ToggleSwitch";

export default function MovementsPage() {
    const { config, saveConfig, error } = useConfig();

    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    const [showFailsafeModal, setShowFailsafeModal] = useState(false);

    useEffect(() => {
        if (!showFailsafeModal) return;

        (window as any).onCalibrationResult = async (data: any) => {
            if (!data || typeof data.key !== "string" || !data.key.startsWith("egg_click_failsafe_")) return;

            const idxStr = data.key.replace("egg_click_failsafe_", "");
            const idx = parseInt(idxStr);
            if (isNaN(idx)) return;

            let val = data.value;
            if (val && Array.isArray(val) && val.length >= 2) {
                const arr = config.egg_click_failsafe ? [...config.egg_click_failsafe] : [];
                arr[idx] = [Math.round(val[0]), Math.round(val[1])];
                const cleaned = { ...config, egg_click_failsafe: arr };
                delete (cleaned as any)[data.key];
                saveConfig(cleaned);
            }
        };

        return () => {
            delete (window as any).onCalibrationResult;
        };
    }, [showFailsafeModal, config]);

    return (
        <>
            {showFailsafeModal && (
                <div style={{
                    position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: "rgba(0,0,0,0.8)", zIndex: 9999,
                    display: "flex", justifyContent: "center", alignItems: "center"
                }}>
                    <div style={{
                        background: "var(--bg-color, #1e1e24)", padding: "20px", borderRadius: "8px",
                        width: "90%", maxWidth: "500px", maxHeight: "80vh", overflowY: "auto",
                        border: "1px solid var(--border-color, #333)"
                    }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
                            <h3 style={{ margin: 0 }}>Configure Egg Path Failsafe</h3>
                            <button className="btn btn-sm" onClick={() => setShowFailsafeModal(false)}>Close</button>
                        </div>

                        <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "15px" }}>
                            Add failsafe click actions that will execute after an egg path finishes.
                        </p>

                        <button
                            className="btn"
                            style={{ width: "100%", padding: "8px", marginBottom: "15px", background: "var(--accent)" }}
                            onClick={() => {
                                const arr = config.egg_click_failsafe ? [...config.egg_click_failsafe] : [];
                                arr.push([0, 0]);
                                updateConfig("egg_click_failsafe", arr);
                            }}
                        >
                            + Add mouse click action
                        </button>

                        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                            {(config.egg_click_failsafe || []).map((pt: [number, number], idx: number) => (
                                <div key={idx} style={{ display: "flex", alignItems: "center", gap: "10px", background: "rgba(255,255,255,0.05)", padding: "10px", borderRadius: "6px" }}>
                                    <span style={{ fontWeight: "bold", width: "30px", color: "var(--text-muted)" }}>#{idx + 1}</span>
                                    <div style={{ flex: 1, display: "flex", gap: "10px" }}>
                                        <span style={{ fontSize: "14px", alignSelf: "center" }}>X:</span>
                                        <input className="form-input" style={{ width: "65px", textAlign: "center" }} type="number" value={pt[0]} onChange={(e) => {
                                            const a = [...config.egg_click_failsafe]; a[idx] = [...a[idx]]; a[idx][0] = parseInt(e.target.value) || 0; updateConfig("egg_click_failsafe", a);
                                        }} />
                                        <span style={{ fontSize: "14px", alignSelf: "center" }}>Y:</span>
                                        <input className="form-input" style={{ width: "65px", textAlign: "center" }} type="number" value={pt[1]} onChange={(e) => {
                                            const a = [...config.egg_click_failsafe]; a[idx] = [...a[idx]]; a[idx][1] = parseInt(e.target.value) || 0; updateConfig("egg_click_failsafe", a);
                                        }} />
                                    </div>
                                    <button className="btn btn-sm" style={{ background: "var(--accent)", color: "white" }} onClick={() => {
                                        if (window.pywebview?.api) window.pywebview.api.create_calibration_window(`egg_click_failsafe_${idx}`, "point");
                                    }}>Select Pos</button>
                                    <button className="btn btn-sm" style={{ background: "#ef4444", color: "white", padding: "4px 8px" }} onClick={() => {
                                        const a = [...config.egg_click_failsafe]; a.splice(idx, 1); updateConfig("egg_click_failsafe", a);
                                    }}>X</button>
                                </div>
                            ))}
                            {(!config.egg_click_failsafe || config.egg_click_failsafe.length === 0) && (
                                <div style={{ textAlign: "center", color: "var(--text-muted)", padding: "15px" }}>No click actions added yet.</div>
                            )}
                        </div>
                    </div>
                </div>
            )}

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
                    description="Slow down to applied movement paths (egg collection, basic obby, fishing, etc...) to compensate for non-VIP walkspeed"
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

            {/* Collect Easter Egg Section */}
            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🥚</div>
                    <div>
                        <h3>Collect Easter Egg</h3>
                        <p>Automatically collect easter eggs spawned around the map</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable Easter Egg Collection"
                    description="Walk around the map to collect easter eggs at set intervals."
                    checked={config.collect_easter_egg || false}
                    onChange={(val) => updateConfig("collect_easter_egg", val)}
                />

                {config.collect_easter_egg && (
                    <>
                        <div className="form-row" style={{ marginTop: "8px" }}>
                            <div className="form-group">
                                <label className="form-label">Collection interval (minutes)</label>
                                <input
                                    className="form-input"
                                    type="number"
                                    min="1"
                                    value={config.egg_collect_interval_min ?? "5"}
                                    onChange={(e) => updateConfig("egg_collect_interval_min", e.target.value)}
                                    style={{ width: "90px" }}
                                />
                            </div>
                        </div>
                        {Number(config.egg_collect_interval_min || 0) < 5 && (
                            <div className="info-banner" style={{ marginTop: "10px", color: "var(--warning-color, #ffaa00)" }}>
                                ⚠️ Warning: Setting the interval too low (under 5 minutes) is highly inefficient! It is strongly recommended to set it around 20-30 minutes per run.
                            </div>
                        )}

                        <div className="form-row" style={{ marginTop: "15px", marginLeft: "10px", paddingBottom: "10px" }}>
                            <div className="form-group">
                                <label className="form-label" style={{ fontWeight: "bold" }}>Egg Path Playback Multiplier (FPS Compensation)</label>
                                <p style={{ margin: "2px 0 8px 0", fontSize: "0.85em", color: "var(--text-color)", opacity: 0.8 }}>
                                    If you get stuck or fall off during paths (due to low FPS), increase this (e.g. 1.1 or 1.25). Higher multiplier = character walks for longer (otherwise keep it at 1.0 if you got consistent fps around 60+)
                                </p>
                                <input
                                    className="form-input"
                                    type="number"
                                    step="0.01"
                                    min="1.0"
                                    max="2.0"
                                    value={config.egg_playback_multiplier ?? "1.0"}
                                    onChange={(e) => updateConfig("egg_playback_multiplier", e.target.value)}
                                    onBlur={(e) => {
                                        let val = parseFloat(e.target.value);
                                        if (isNaN(val) || val < 1.0) updateConfig("egg_playback_multiplier", "1.0");
                                    }}
                                    style={{ width: "90px" }}
                                />
                            </div>
                        </div>
                        {Number(config.egg_playback_multiplier) < 1 && (
                            <div className="info-banner" style={{ marginTop: "5px", color: "var(--warning-color, #ffaa00)" }}>
                                ⚠️ If you set the multiplier below 1.0, the macro will automatically default it back to 1.0 :aga:
                            </div>
                        )}

                        <div style={{ marginTop: "15px", padding: "10px", borderBottom: "1px solid var(--border-color)", borderTop: "1px solid var(--border-color)" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <button
                                    className="btn"
                                    onClick={() => setShowFailsafeModal(true)}
                                    style={{ padding: "8px 16px", background: "rgba(239, 68, 68, 0.15)", color: "#ef4444", border: "1px solid rgba(239, 68, 68, 0.3)" }}
                                >
                                    Configure Egg Path Failsafe
                                </button>
                            </div>
                        </div>
                    </>
                )}

                <ToggleSwitch
                    label="Equip an aura before egg collection"
                    description="Before walking to collect eggs, equip the aura name below using Aura calibration (under Macro Calibrations)"
                    checked={config.equip_aura_before_egg_collect || false}
                    onChange={(val) => updateConfig("equip_aura_before_egg_collect", val)}
                />
                {config.equip_aura_before_egg_collect && (
                    <div className="form-row" style={{ marginTop: "8px" }}>
                        <div className="form-group">
                            <label className="form-label">Aura name to equip</label>
                            <input
                                className="form-input"
                                value={config.egg_collect_aura_name || ""}
                                onChange={(e) => updateConfig("egg_collect_aura_name", e.target.value)}
                                style={{ width: "220px" }}
                                placeholder="Enter aura name"
                            />
                        </div>
                    </div>
                )}

                <div style={{ marginTop: "15px", borderTop: "1px solid var(--border-color)", paddingTop: "15px" }}>
                    <ToggleSwitch
                        label="OCR check to detect special egg on roblox chat (optional)"
                        description="Use OCR to read the roblox chat box for special egg messages. Requires Roblox Chat Box Region calibration."
                        checked={config.egg_ocr_detect_special || false}
                        onChange={(val) => updateConfig("egg_ocr_detect_special", val)}
                    />

                    {config.egg_ocr_detect_special && (
                        <>
                            <div className="form-row" style={{ marginTop: "8px" }}>
                                <div className="form-group">
                                    <label className="form-label">Your Discord User ID (to ping whenever special egg is found on roblox chat)</label>
                                    <input
                                        className="form-input"
                                        type="text"
                                        value={config.egg_ocr_discord_userid || ""}
                                        onChange={(e) => updateConfig("egg_ocr_discord_userid", e.target.value)}
                                        placeholder="Enter your Discord user ID"
                                        style={{ width: "220px" }}
                                    />
                                </div>
                            </div>

                            <div className="info-banner" style={{ marginTop: "10px" }}>
                                ⚠️ Enabling this OCR feature would HAVE A CHANCE of false detection of special eggs so use it with your caution!! (Simply ignore the ping if it does that)
                            </div>

                            <div className="info-banner" style={{ marginTop: "10px", opacity: 0.85 }}>
                                ℹ️ Egg OCR check will temporarily stop during: Rare biomes (Glitched, Dreamspace, Cyberspace), reconnecting, egg collection pathing, fishing (when is in reeling minigame), basic obby, merchant was found and in autobuy stage, potion crafting, auto pop is ON (Except for Idle mode)
                            </div>
                        </>
                    )}
                </div>
            </div>
        </>
    );
}
