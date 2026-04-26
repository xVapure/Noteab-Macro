import { useConfig } from "../contexts/ConfigContext";
import { useState, useEffect } from "react";

type CalibrationField = {
    key: string;
    label: string;
    isRegion?: boolean;
};

type CalibrationGroup = {
    id: string;
    label: string;
    color: string;
    fields: CalibrationField[];
};

type MouseActionRequirement = {
    feature: string;
    page: string;
    calibrations: string[];
};

const CALIBRATION_GROUPS: CalibrationGroup[] = [
    {
        id: "movements",
        label: "Movements Calibration",
        color: "#d4a843",
        fields: [
            { key: "collections_button", label: "Collection Menu" },
            { key: "exit_collections_button", label: "Exit Collection" },
            { key: "chat_hover_pos", label: "Roblox Chat Box" },
            { key: "chat_tab_ocr_pos", label: "Chat Tab OCR Region (either 'General' or 'Server Message')", isRegion: true },
            { key: "chat_close_button", label: "Roblox Chat Icon (to close chat box)" },
            { key: "chat_box_ocr_pos", label: "Chat Box OCR Region (to reads text inside Roblox chat)", isRegion: true },

        ]
    },
    {
        id: "quest",
        label: "Quest Claim Calibration",
        color: "#d4a843",
        fields: [
            { key: "quest_menu", label: "Quest Menu Button" },
            { key: "quest1_button", label: "Quest 1 Position" },
            { key: "quest2_button", label: "Quest 2 Position" },
            { key: "quest3_button", label: "Quest 3 Position" },
            { key: "claim_quest_button", label: "Claim Button" },
            { key: "quest_reroll_button", label: "Reroll Button" },
        ]
    },
    {
        id: "merchant",
        label: "Merchant Calibrations",
        color: "#7c5bf5",
        fields: [
            { key: "merchant_open_button", label: "Open Button" },
            { key: "merchant_dialogue_box", label: "Dialogue Box" },
            { key: "purchase_amount_button", label: "Amount Input" },
            { key: "purchase_button", label: "Purchase Button" },
            { key: "first_item_merchant_slot_pos", label: "First Item Slot" },
            { key: "merchant_close_button", label: "Sell Menu Close Button" },
            { key: "merchant_name_ocr_pos", label: "Merchant Name OCR Region", isRegion: true },
            { key: "item_name_ocr_pos", label: "Item Name OCR Region", isRegion: true },
        ]
    },
    {
        id: "buff",
        label: "Enable Buff Calibration",
        color: "#ef4444",
        fields: [
            { key: "glitched_menu_button", label: "Menu Button" },
            { key: "glitched_settings_button", label: "Settings Button" },
            { key: "glitched_buff_enable_button", label: "Buff Toggle" },
        ]
    },
    {
        id: "aura",
        label: "Equip Aura Calibration",
        color: "#ec4899",
        fields: [
            { key: "aura_menu", label: "Aura Menu" },
            { key: "aura_search_bar", label: "Aura Search Bar Calibration (X,Y)" },
            { key: "first_aura_slot_pos", label: "First Aura Slot" },
            { key: "equip_aura_button", label: "Equip Aura Button" },
        ]
    },
    {
        id: "inventory",
        label: "Inventory Click Calibration",
        color: "#22c55e",
        fields: [
            { key: "inventory_menu", label: "Inventory Menu" },
            { key: "items_tab", label: "Items Tab" },
            { key: "search_bar", label: "Search Bar" },
            { key: "first_item_inventory_slot_pos", label: "First Inventory Item Slot" },
            { key: "amount_box", label: "Amount Box" },
            { key: "use_button", label: "Use Button" },
            { key: "inventory_close_button", label: "Inventory Close Button" },
            { key: "reconnect_start_button", label: "Join Button in Sol's RNG" },
            { key: "first_item_slot_ocr_pos", label: "First Item Slot OCR Region", isRegion: true },
        ]
    },
    {
        id: "potion",
        label: "Potion Crafting Calibration",
        color: "#0ea5e9",
        fields: [
            { key: "potion_items_tab", label: "Stella's Items Tab" },
            { key: "potion_search_bar", label: "Stella's Search Bar" },
            { key: "potion_first_potion_slot_pos", label: "First Potion Slot" },
            { key: "potion_recipe_button", label: "Open Recipe Button" },
            { key: "potion_auto_add_button", label: "Auto Add button" },
        ]
    },
    {
        id: "fishing",
        label: "Fishing Calibration",
        color: "#06b6d4",
        fields: [
            { key: "fishing_bar_region", label: "Fishing Bar Region", isRegion: true },
            { key: "fishing_detect_pixel", label: "Fish Indicator Pixel" },
            { key: "fishing_click_position", label: "Start fishing button" },
            { key: "fishing_midbar_sample_pos", label: "Mid Bar Color Sample" },
            { key: "fishing_close_button_pos", label: "Close Button" },
            { key: "fishing_flarg_dialogue_box", label: "Captain Flarg Dialogue Box" },
            { key: "fishing_shop_open_button", label: "Open Fishing Shop" },
            { key: "fishing_shop_sell_tab", label: "Fishing Shop Sell Tab" },
            { key: "fishing_shop_close_button", label: "Close Fishing Shop" },
            { key: "fishing_shop_first_fish", label: "First Fish In Shop" },
            { key: "fishing_shop_sell_all_button", label: "Sell All Button" },
            { key: "fishing_confirm_sell_all_button", label: "Confirm Sell All Button" },
        ]
    }
];

const CALIBRATION_MODE_BY_KEY = CALIBRATION_GROUPS.reduce((acc, group) => {
    group.fields.forEach((field) => {
        acc[field.key] = field.isRegion ? "region" : "point";
    });
    return acc;
}, {} as Record<string, "point" | "region">);

const MOUSE_ACTION_REQUIREMENTS: MouseActionRequirement[] = [
    { page: "Fishing", feature: "Fishing Mode Core Loop", calibrations: ["Fishing Calibration"] },
    { page: "Fishing", feature: "Fishing Auto Sell", calibrations: ["Fishing Calibration"] },
    { page: "Fishing", feature: "Fishing Auto Merchant Every X Fish", calibrations: ["Inventory Click Calibration", "Merchant Calibrations"] },
    { page: "Fishing", feature: "Fishing BR/SC Every X Fish", calibrations: ["Inventory Click Calibration"] },

    { page: "Merchant", feature: "Auto Merchant Teleporter", calibrations: ["Inventory Click Calibration", "Merchant Calibrations"] },
    { page: "Merchant", feature: "Auto Merchant in Limbo", calibrations: ["Inventory Click Calibration", "Merchant Calibrations"] },

    { page: "Misc", feature: "Biome Randomizer (BR)", calibrations: ["Inventory Click Calibration"] },
    { page: "Misc", feature: "Strange Controller (SC)", calibrations: ["Inventory Click Calibration"] },
    { page: "Auto Pop Buff", feature: "Auto Pop Buffs", calibrations: ["Inventory Click Calibration"] },
    { page: "Misc", feature: "Auto Reconnect (Join Button in Sol's RNG)", calibrations: ["Inventory Click Calibration"] },
    { page: "Misc", feature: "Periodical Aura Screenshot", calibrations: ["Equip Aura Calibration", "Inventory Click Calibration"] },
    { page: "Misc", feature: "Periodical Inventory Screenshot", calibrations: ["Inventory Click Calibration"] },
    { page: "Misc", feature: "Auto Claim Daily Quests", calibrations: ["Quest Claim Calibration"] },
    { page: "Misc", feature: "OCR Failsafe", calibrations: ["Inventory Click Calibration"] },

    { page: "Other Features", feature: "Enable Buff in Glitched/Dreamspace", calibrations: ["Enable Buff Calibration"] },
    { page: "Other Features", feature: "Teleport Back to Limbo", calibrations: ["Inventory Click Calibration"] },

    { page: "Movements", feature: "Auto Complete Basic Obby", calibrations: ["Movements Calibration"] },
    { page: "Movements", feature: "Use Float Aura", calibrations: ["Equip Aura Calibration", "Inventory Click Calibration"] },
    { page: "Movements", feature: "Easter Egg Collection", calibrations: ["Movements Calibration"] },
    { page: "Movements", feature: "Easter Egg OCR Special Detection", calibrations: ["Movements Calibration"] },

    { page: "Potion Craft", feature: "Potion Auto Craft / Switching", calibrations: ["Potion Crafting Calibration"] },

    { page: "Remote", feature: "Remote check_merchant command", calibrations: ["Inventory Click Calibration", "Merchant Calibrations"] },
    { page: "Remote", feature: "Remote use item command", calibrations: ["Inventory Click Calibration"] },
];

function normalizeCalibrationData(data: any, expectedMode: "point" | "region"): number[] | null {
    let value: unknown = data?.value;

    if (!Array.isArray(value)) {
        if (expectedMode === "region" && data && data.x !== undefined && data.y !== undefined && data.w !== undefined && data.h !== undefined) {
            value = [data.x, data.y, data.w, data.h];
        } else if (expectedMode === "point" && data && data.x !== undefined && data.y !== undefined) {
            value = [data.x, data.y];
        } else {
            return null;
        }
    }

    const arr = value as unknown[];
    const expectedLength = expectedMode === "region" ? 4 : 2;
    if (arr.length < expectedLength) return null;

    const normalized = arr.slice(0, expectedLength).map((v: any) => Math.round(Number(v)));
    if (normalized.some((n) => !Number.isFinite(n))) return null;

    if (expectedMode === "region" && (normalized[2] <= 0 || normalized[3] <= 0)) return null;
    return normalized;
}

// Helper component for coordinate inputs
function CoordInput({ label, value, onChange, isRegion = false, onCalibrate }: {
    label: string,
    value: number[],
    onChange: (val: number[]) => void,
    isRegion?: boolean,
    onCalibrate: () => void
}) {
    const vals = value || (isRegion ? [0, 0, 0, 0] : [0, 0]);

    const update = (idx: number, val: string) => {
        const num = parseInt(val) || 0;
        const next = [...vals];
        next[idx] = num;
        onChange(next);
    };

    return (
        <div className="coord-input-group" style={{ marginBottom: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <label style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500 }}>
                        {label}
                    </label>
                </div>
                <button
                    className="btn btn-sm"
                    style={{
                        fontSize: "10px",
                        padding: "2px 8px",
                        background: "var(--accent)",
                        color: "white",
                        opacity: 0.9,
                        border: "none",
                        borderRadius: "2px",
                        letterSpacing: "0.5px",
                        boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
                        height: "20px",
                        display: "flex",
                        alignItems: "center",
                        cursor: "pointer"
                    }}
                    onClick={onCalibrate}
                >
                    {isRegion ? "SELECT REGION" : "SELECT POS"}
                </button>
            </div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                {/* X */}
                <div className="coord-box">
                    <span className="coord-label">X</span>
                    <input className="coord-input" type="number" value={vals[0]} onChange={(e) => update(0, e.target.value)} />
                </div>
                {/* Y */}
                <div className="coord-box">
                    <span className="coord-label">Y</span>
                    <input className="coord-input" type="number" value={vals[1]} onChange={(e) => update(1, e.target.value)} />
                </div>
                {/* W/H if region */}
                {isRegion && (
                    <>
                        <div className="coord-box">
                            <span className="coord-label">W</span>
                            <input className="coord-input" type="number" value={vals[2]} onChange={(e) => update(2, e.target.value)} />
                        </div>
                        <div className="coord-box">
                            <span className="coord-label">H</span>
                            <input className="coord-input" type="number" value={vals[3]} onChange={(e) => update(3, e.target.value)} />
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}

export default function CalibrationPage() {
    const { config, setConfig, saveConfig, error } = useConfig();
    const [expandedSection, setExpandedSection] = useState<string | null>(null);

    useEffect(() => {
        (window as any).onCalibrationResult = async (data: any) => {
            if (!data || typeof data.key !== "string") return;

            const expectedMode = CALIBRATION_MODE_BY_KEY[data.key] || "point";
            const value = normalizeCalibrationData(data, expectedMode);
            if (!value) {
                console.warn("Ignored invalid calibration payload:", data);
                return;
            }

            try {
                if (window.pywebview?.api?.get_config) {
                    const latestConfig = await window.pywebview.api.get_config();
                    if (latestConfig && typeof latestConfig === "object") {
                        setConfig({ ...latestConfig, [data.key]: value });
                        return;
                    }
                }
            } catch (err) {
                console.warn("Failed to refresh config after calibration:", err);
            }

            if (config) {
                setConfig({ ...config, [data.key]: value });
            }
        };

        return () => {
            delete (window as any).onCalibrationResult;
        };
    }, [config, setConfig]);

    const startCalibration = async (key: string, isRegion: boolean) => {
        try {
            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.create_calibration_window(key, isRegion ? "region" : "point");
            }
        } catch (e) {
            console.error("Failed to open calibration window", e);
            alert("Failed to open calibration tool: " + e);
        }
    };

    // CSS for compact inputs
    const styles = `
        .coord-box { display: flex; align-items: center; background: var(--bg-input); border: 1px solid var(--border); border-radius: 4px; overflow: hidden; }
        .coord-label { padding: 0 6px; font-size: 11px; color: var(--text-muted); background: rgba(255,255,255,0.05); border-right: 1px solid var(--border); height: 100%; display: flex; align-items: center; }
        .coord-input { border: none; background: transparent; color: var(--text-primary); padding: 4px; width: 45px; font-size: 12px; outline: none; text-align: center; }
        .coord-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
    `;

    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    const toggleSection = (section: string) => {
        setExpandedSection(expandedSection === section ? null : section);
    };

    const [showRequirements, setShowRequirements] = useState(false);
    const [presets, setPresets] = useState<any[]>([]);
    const [selectedRes, setSelectedRes] = useState("");
    const [selectedScale, setSelectedScale] = useState("");
    const [selectedMode, setSelectedMode] = useState("");
    const [showPresetModal, setShowPresetModal] = useState(false);
    const [pendingPreset, setPendingPreset] = useState<any>(null);

    useEffect(() => {
        fetch("https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/macro_calibs_preset.json")
            .then(res => res.json())
            .then(data => {
                if (data && Array.isArray(data.presets)) {
                    setPresets(data.presets);
                }
            })
            .catch(err => console.warn("Failed to load calibration presets via Github fetching", err));
    }, []);

    const uniqueResolutions = Array.from(new Set(presets.map(p => p.resolution)));
    const availableScales = Array.from(new Set(presets.filter(p => p.resolution === selectedRes).map(p => p.scale)));
    const availableModes = Array.from(new Set(presets.filter(p => p.resolution === selectedRes && p.scale === selectedScale).map(p => p.mode)));

    const handleApplyClick = () => {
        const preset = presets.find(p => p.resolution === selectedRes && p.scale === selectedScale && p.mode === selectedMode);
        if (!preset || !preset.calibrations) {
            alert("Please select a valid preset (Resolution, Scale, and Mode)");
            return;
        }
        setPendingPreset(preset);
        setShowPresetModal(true);
    };

    const [presetStatus, setPresetStatus] = useState<string>("");

    const confirmPresetApply = async () => {
        if (pendingPreset && pendingPreset.calibrations) {
            const newConfig = { ...config, ...pendingPreset.calibrations };
            try {
                await saveConfig(newConfig);
                setPresetStatus(`Preset applied: ${pendingPreset.resolution} (${pendingPreset.scale} ${pendingPreset.mode})`);
                setTimeout(() => setPresetStatus(""), 5000);
            } catch (err) {
                setPresetStatus("Failed to apply preset: " + String(err));
                setTimeout(() => setPresetStatus(""), 5000);
            }
        }
        setShowPresetModal(false);
        setPendingPreset(null);
    };

    return (
        <>
            <style>{styles}</style>

            {/* Preset Confirm Modal */}
            {showPresetModal && pendingPreset && (
                <div className="biome-confirm-overlay" onClick={() => setShowPresetModal(false)}>
                    <div className="biome-confirm-modal" onClick={e => e.stopPropagation()} style={{ textAlign: "left" }}>
                        <h3 className="biome-confirm-title" style={{ textAlign: "center" }}>Overwrite Calibrations?</h3>
                        <p style={{ color: "var(--text-secondary)", marginBottom: "20px", lineHeight: "1.6", textAlign: "center", fontSize: "14px" }}>
                            This will overwrite your current calibrations with the
                            <br />
                            <strong style={{ color: "var(--text-primary)" }}>{pendingPreset.resolution} ({pendingPreset.scale} {pendingPreset.mode})</strong> preset.
                            <br /><br />
                            <span style={{ color: "var(--text-muted)", fontSize: "0.85em" }}>This action cannot be undone.</span>
                        </p>
                        <div className="biome-confirm-buttons">
                            <button className="biome-confirm-btn confirm" onClick={confirmPresetApply}>Yes, Overwrite</button>
                            <button className="biome-confirm-btn cancel" onClick={() => setShowPresetModal(false)}>Cancel</button>
                        </div>
                    </div>
                </div>
            )}

            <div className="page-header">
                <h2>Macro Calibrations</h2>
                <p>View and manually edit calibration coordinates</p>
            </div>

            <div className="info-banner" style={{ marginBottom: "16px" }}>
                <div>ℹ️ Use "Select Pos" or "Select Region" to launch the calibration overlay :)</div>
                <div style={{ marginTop: "6px" }}>
                    If you have troubles understanding refer to this tutorial:{" "}
                    <a href="https://www.youtube.com/watch?v=s2S7Bncx9ns" target="_blank" rel="noreferrer">
                        https://www.youtube.com/watch?v=s2S7Bncx9ns
                    </a>
                </div>
            </div>

            {/* Mouse Action Requirements Section*/}
            <div className="card" style={{ padding: "0", marginBottom: "16px" }}>
                <div
                    className="card-header"
                    style={{
                        padding: "16px",
                        cursor: "pointer",
                        borderBottom: showRequirements ? "1px solid var(--border-color)" : "none"
                    }}
                    onClick={() => setShowRequirements(!showRequirements)}
                >
                    <div className="card-icon">🧭</div>
                    <div style={{ flex: 1 }}>
                        <h3>Mouse Action Calibration Requirements</h3>
                        <p>Feature-to-calibration tracking for actions that use mouse inputs</p>
                    </div>
                    <div>{showRequirements ? "▲" : "▼"}</div>
                </div>

                {showRequirements && (
                    <div style={{ padding: "16px" }}>
                        <div className="form-hint" style={{ marginBottom: "8px" }}>
                            Note: Features using OCR failsafe also require calibrating First Item Slot OCR Region under Inventory Click Calibration.
                        </div>
                        <div style={{ display: "grid", gap: "8px" }}>
                            {MOUSE_ACTION_REQUIREMENTS.map((item) => (
                                <div
                                    key={item.feature}
                                    style={{
                                        display: "grid",
                                        gridTemplateColumns: "120px 1fr 1fr",
                                        gap: "10px",
                                        alignItems: "center",
                                        padding: "8px 10px",
                                        border: "1px solid var(--border-color)",
                                        borderRadius: "6px",
                                        background: "rgba(255,255,255,0.02)"
                                    }}
                                >
                                    <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>{item.page}</div>
                                    <div style={{ fontSize: "13px", color: "var(--text-primary)" }}>{item.feature}</div>
                                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                                        {item.calibrations.join(" + ")}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Macro Calibrations Preset */}
            <div className="card" style={{ marginBottom: "16px" }}>
                <div className="card-header">
                    <div className="card-icon">⚡</div>
                    <div style={{ flex: 1 }}>
                        <h3>Macro Calibrations Preset</h3>
                        <p>Pre-made macro calibrations for common screen resolutions, display scales, and window modes (so u don't have to set it up manually :umamusume_mambo_dancing:)</p>
                    </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: "10px", alignItems: "end", marginTop: "12px" }}>
                    <div>
                        <label style={{ display: "block", fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px", letterSpacing: "0.5px" }}>RESOLUTION</label>
                        <select
                            className="form-input"
                            style={{ width: "100%", cursor: "pointer" }}
                            value={selectedRes}
                            onChange={(e) => {
                                setSelectedRes(e.target.value);
                                setSelectedScale("");
                                setSelectedMode("");
                            }}
                        >
                            <option value="">Select Resolution</option>
                            {uniqueResolutions.map((res: any) => (
                                <option key={res} value={res}>{res}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label style={{ display: "block", fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px", letterSpacing: "0.5px" }}>DISPLAY SCALE</label>
                        <select
                            className="form-input"
                            style={{ width: "100%", cursor: selectedRes ? "pointer" : "not-allowed", opacity: selectedRes ? 1 : 0.5 }}
                            value={selectedScale}
                            onChange={(e) => {
                                setSelectedScale(e.target.value);
                                setSelectedMode("");
                            }}
                            disabled={!selectedRes}
                        >
                            <option value="">Select Scale</option>
                            {availableScales.map((scale: any) => (
                                <option key={scale} value={scale}>{scale}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label style={{ display: "block", fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px", letterSpacing: "0.5px" }}>WINDOW MODE</label>
                        <select
                            className="form-input"
                            style={{ width: "100%", cursor: selectedScale ? "pointer" : "not-allowed", opacity: selectedScale ? 1 : 0.5 }}
                            value={selectedMode}
                            onChange={(e) => setSelectedMode(e.target.value)}
                            disabled={!selectedScale}
                        >
                            <option value="">Select Mode</option>
                            {availableModes.map((mode: any) => (
                                <option key={mode} value={mode}>{mode}</option>
                            ))}
                        </select>
                    </div>

                    <button
                        className="btn btn-accent"
                        onClick={handleApplyClick}
                        disabled={!selectedRes || !selectedScale || !selectedMode}
                        style={{ height: "36px", whiteSpace: "nowrap" }}
                    >
                        Apply Preset
                    </button>
                </div>
                {presets.length === 0 && (
                    <div style={{ color: "var(--text-muted)", fontSize: "12px", marginTop: "8px" }}>
                        Presets not found on github or failed to fetch.
                    </div>
                )}
                {presetStatus && (
                    <div style={{
                        marginTop: "10px",
                        padding: "8px 14px",
                        borderRadius: "6px",
                        fontSize: "13px",
                        fontWeight: 500,
                        background: presetStatus.startsWith("✅") ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                        color: presetStatus.startsWith("✅") ? "#22c55e" : "#ef4444",
                        border: `1px solid ${presetStatus.startsWith("✅") ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
                    }}>
                        {presetStatus}
                    </div>
                )}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {CALIBRATION_GROUPS.map((group) => (
                    <div key={group.id} className="card" style={{ padding: "0" }}>
                        <div
                            className="card-header"
                            style={{
                                padding: "16px",
                                cursor: "pointer",
                                borderBottom: expandedSection === group.id ? "1px solid var(--border-color)" : "none"
                            }}
                            onClick={() => toggleSection(group.id)}
                        >
                            <div className="card-icon" style={{ borderColor: group.color }}>🎯</div>
                            <div style={{ flex: 1 }}>
                                <h3 style={{ color: group.color }}>{group.label}</h3>
                                <p>Click to view/edit coordinates</p>
                            </div>
                            <div>{expandedSection === group.id ? "▲" : "▼"}</div>
                        </div>

                        {expandedSection === group.id && (
                            <div style={{ padding: "16px", background: "rgba(0,0,0,0.2)" }}>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                                    {group.fields.map((field) => (
                                        <CoordInput
                                            key={field.key}
                                            label={field.label}
                                            value={config[field.key]}
                                            onChange={(val) => updateConfig(field.key, val)}
                                            isRegion={field.isRegion}
                                            onCalibrate={() => startCalibration(field.key, field.isRegion || false)}
                                        />
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </>
    );
}