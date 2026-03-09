import { useConfig } from "../contexts/ConfigContext";
import { useState, useEffect } from "react";
// Remove tauri imports

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

    return (
        <>
            <style>{styles}</style>
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

            <div className="card" style={{ marginBottom: "16px" }}>
                <div className="card-header">
                    <div className="card-icon">🧭</div>
                    <div>
                        <h3>Mouse Action Calibration Requirements</h3>
                        <p>Feature-to-calibration tracking for actions that use mouse inputs</p>
                    </div>
                </div>
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
