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
        id: "dailyRewards",
        label: "Claim Daily Quest Calibration",
        color: "#d4a843",
        fields: [
            { key: "daily_reward_claim_button", label: "Claim Button" },
            { key: "daily_reward_close_button", label: "Close Button" },
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
            { key: "autobuy_set_to_max_button", label: "Autobuy - Set to Max" },
            { key: "first_item_merchant_slot_pos", label: "First Item Slot" },
            { key: "second_item_merchant_slot_pos", label: "Second Item Slot" },
            { key: "third_item_merchant_slot_pos", label: "Third Item Slot" },
            { key: "fourth_item_merchant_slot_pos", label: "Fourth Item Slot" },
            { key: "fifth_item_merchant_slot_pos", label: "Fifth Item Slot" },
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
            { key: "fishing_bugged_ui_pos", label: "Bugged Fishing UI (click when stuck)" },
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
    { page: "Misc", feature: "Claim Daily Rewards", calibrations: ["Claim Daily Quest Calibration"] },
    { page: "Misc", feature: "OCR Failsafe", calibrations: ["Inventory Click Calibration"] },

    { page: "Other Features", feature: "Enable Buff in Glitched/Dreamspace", calibrations: ["Enable Buff Calibration"] },
    { page: "Other Features", feature: "Teleport Back to Limbo", calibrations: ["Inventory Click Calibration"] },

    { page: "Movements", feature: "Auto Complete Basic Obby", calibrations: ["Movements Calibration"] },
    { page: "Movements", feature: "Use Float Aura", calibrations: ["Equip Aura Calibration", "Inventory Click Calibration"] },
    { page: "Movements", feature: "Easter Egg Collection", calibrations: ["Movements Calibration"] },
    { page: "Movements", feature: "Easter Egg OCR Special Detection", calibrations: ["Movements Calibration"] },

    { page: "Potion Craft", feature: "Potion Auto Craft / Switching", calibrations: ["Potion Crafting Calibration"] },

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

                <div className="coord-box">
                    <span className="coord-label">X</span>
                    <input className="coord-input" type="number" value={vals[0]} onChange={(e) => update(0, e.target.value)} />
                </div>

                <div className="coord-box">
                    <span className="coord-label">Y</span>
                    <input className="coord-input" type="number" value={vals[1]} onChange={(e) => update(1, e.target.value)} />
                </div>

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

const DEFAULT_LOCAL_PRESETS = [
    {
        resolution: "1366x768",
        scale: "100%",
        mode: "Fullscreen",
        calibrations: {
            collections_button: [28, 329],
            exit_collections_button: [272, 108],
            chat_hover_pos: [229, 200],
            chat_tab_ocr_pos: [247, 60, 255, 43],
            chat_close_button: [137, 32],
            chat_box_ocr_pos: [15, 228, 522, 59],
            quest_menu: [29, 436],
            quest1_button: [728, 371],
            quest2_button: [648, 427],
            quest3_button: [762, 476],
            claim_quest_button: [443, 547],
            quest_reroll_button: [445, 404],
            merchant_open_button: [404, 662],
            merchant_dialogue_box: [872, 555],
            purchase_amount_button: [746, 434],
            purchase_button: [731, 461],
            autobuy_set_to_max_button: [949, 435],
            first_item_merchant_slot_pos: [684, 512],
            second_item_merchant_slot_pos: [832, 512],
            third_item_merchant_slot_pos: [980, 512],
            fourth_item_merchant_slot_pos: [684, 612],
            fifth_item_merchant_slot_pos: [832, 612],
            merchant_close_button: [1288, 247],
            merchant_name_ocr_pos: [521, 494, 188, 28],
            item_name_ocr_pos: [790, 268, 358, 17],
            glitched_menu_button: [23, 482],
            glitched_settings_button: [686, 418],
            glitched_buff_enable_button: [931, 652],
            aura_menu: [27, 288],
            aura_search_bar: [585, 262],
            first_aura_slot_pos: [580, 310],
            equip_aura_button: [449, 448],
            inventory_menu: [28, 357],
            items_tab: [882, 237],
            search_bar: [589, 260],
            first_item_inventory_slot_pos: [603, 329],
            amount_box: [406, 408],
            use_button: [490, 409],
            inventory_close_button: [1007, 213],
            reconnect_start_button: [157, 707],
            first_item_slot_ocr_pos: [573, 309, 66, 63],
            potion_items_tab: [1076, 160],
            potion_search_bar: [1037, 186],
            potion_first_potion_slot_pos: [1093, 240],
            potion_recipe_button: [163, 580],
            potion_auto_add_button: [304, 581],
            fishing_bar_region: [507, 526, 353, 24],
            fishing_detect_pixel: [865, 593],
            fishing_click_position: [588, 588],
            fishing_midbar_sample_pos: [682, 529],
            fishing_close_button_pos: [816, 212],
            fishing_flarg_dialogue_box: [820, 549],
            fishing_shop_open_button: [462, 664],
            fishing_shop_sell_tab: [916, 218],
            fishing_shop_close_button: [1038, 189],
            fishing_shop_first_fish: [592, 295],
            fishing_shop_sell_all_button: [472, 568],
            fishing_confirm_sell_all_button: [563, 439],
            fishing_bugged_ui_pos: [860, 331],
            daily_reward_claim_button: [686, 470],
            daily_reward_close_button: [1008, 282]
        }
    },
    {
        resolution: "2560x1440",
        scale: "100%",
        mode: "Fullscreen",
        calibrations: {
            collections_button: [52, 616],
            exit_collections_button: [510, 177],
            chat_hover_pos: [366, 377],
            chat_tab_ocr_pos: [383, 100, 315, 46],
            chat_close_button: [206, 47],
            chat_box_ocr_pos: [23, 383, 686, 111],
            quest_menu: [51, 828],
            quest1_button: [1257, 692],
            quest2_button: [1253, 800],
            quest3_button: [1387, 900],
            claim_quest_button: [821, 1015],
            quest_reroll_button: [805, 746],
            merchant_open_button: [832, 1263],
            merchant_dialogue_box: [975, 810],
            purchase_amount_button: [1055, 609],
            purchase_button: [1574, 878],
            autobuy_set_to_max_button: [1333, 595],
            first_item_merchant_slot_pos: [1616, 621],
            second_item_merchant_slot_pos: [1764, 621], 
            third_item_merchant_slot_pos: [1912, 621],
            fourth_item_merchant_slot_pos: [1616, 721],
            fifth_item_merchant_slot_pos: [1764, 721],
            merchant_close_button: [1811, 325],
            merchant_name_ocr_pos: [731, 682, 278, 52],
            item_name_ocr_pos: [1106, 372, 708, 35],
            glitched_menu_button: [51, 897],
            glitched_settings_button: [1244, 780],
            glitched_buff_enable_button: [1242, 870],
            aura_menu: [44, 537],
            aura_search_bar: [1088, 488],
            first_aura_slot_pos: [1098, 579],
            equip_aura_button: [793, 842],
            inventory_menu: [49, 673],
            items_tab: [1555, 447],
            search_bar: [1087, 487],
            first_item_inventory_slot_pos: [1122, 601],
            amount_box: [759, 765],
            use_button: [910, 764],
            inventory_close_button: [1885, 398],
            reconnect_start_button: [292, 1304],
            first_item_slot_ocr_pos: [1075, 581, 112, 111],
            potion_items_tab: [2009, 297],
            potion_search_bar: [1936, 350],
            potion_first_potion_slot_pos: [2016, 442],
            potion_recipe_button: [266, 1087],
            potion_auto_add_button: [568, 1084],
            fishing_bar_region: [989, 1005, 583, 38],
            fishing_detect_pixel: [1585, 1114],
            fishing_click_position: [1115, 1102],
            fishing_midbar_sample_pos: [1279, 1012],
            fishing_close_button_pos: [1499, 439],
            fishing_flarg_dialogue_box: [1578, 1083],
            fishing_shop_open_button: [835, 1250],
            fishing_shop_sell_tab: [1647, 416],
            fishing_shop_close_button: [1945, 355],
            fishing_shop_first_fish: [1068, 524],
            fishing_shop_sell_all_button: [876, 1067],
            fishing_confirm_sell_all_button: [1072, 820],
            fishing_bugged_ui_pos: [1616, 621],
            daily_reward_claim_button: [1285, 881],
            daily_reward_close_button: [1891, 527]
        }
    },
    {
        resolution: "1920x1080",
        scale: "100%",
        mode: "Fullscreen",
        calibrations: {
            collections_button: [35, 463],
            exit_collections_button: [386, 126],
            chat_hover_pos: [70, 192],
            chat_tab_ocr_pos: [242, 62, 241, 40],
            chat_close_button: [140, 35],
            chat_box_ocr_pos: [8, 101, 474, 269],
            quest_menu: [38, 624],
            quest1_button: [1100, 524],
            quest2_button: [1104, 595],
            quest3_button: [1101, 677],
            claim_quest_button: [618, 770],
            quest_reroll_button: [623, 585],
            merchant_open_button: [654, 946],
            merchant_dialogue_box: [768, 836],
            purchase_amount_button: [1044, 611],
            purchase_button: [982, 666],
            autobuy_set_to_max_button: [1000, 446],
            first_item_merchant_slot_pos: [952, 719],
            second_item_merchant_slot_pos: [1100, 719],
            third_item_merchant_slot_pos: [1248, 719],
            fourth_item_merchant_slot_pos: [952, 819],
            fifth_item_merchant_slot_pos: [1100, 819],
            merchant_close_button: [1809, 346],
            merchant_name_ocr_pos: [730, 683, 276, 52],
            item_name_ocr_pos: [870, 697, 946, 48],
            glitched_menu_button: [36, 678],
            glitched_settings_button: [946, 583],
            glitched_buff_enable_button: [929, 654],
            aura_menu: [28, 401],
            aura_search_bar: [809, 361],
            first_aura_slot_pos: [821, 437],
            equip_aura_button: [623, 637],
            inventory_menu: [32, 515],
            items_tab: [1272, 337],
            search_bar: [828, 369],
            first_item_inventory_slot_pos: [846, 480],
            amount_box: [566, 577],
            use_button: [687, 581],
            inventory_close_button: [1413, 301],
            reconnect_start_button: [244, 1003],
            first_item_slot_ocr_pos: [805, 433, 87, 89],
            potion_items_tab: [1507, 227],
            potion_search_bar: [1448, 264],
            potion_first_potion_slot_pos: [1512, 332],
            potion_recipe_button: [200, 815],
            potion_auto_add_button: [426, 813],
            fishing_bar_region: [757, 762, 405, 21],
            fishing_detect_pixel: [1176, 836],
            fishing_click_position: [862, 843],
            fishing_midbar_sample_pos: [955, 767],
            fishing_close_button_pos: [1113, 342],
            fishing_flarg_dialogue_box: [1046, 782],
            fishing_shop_open_button: [616, 938],
            fishing_shop_sell_tab: [1285, 312],
            fishing_shop_close_button: [1458, 269],
            fishing_shop_first_fish: [827, 404],
            fishing_shop_sell_all_button: [662, 799],
            fishing_confirm_sell_all_button: [800, 619],
            fishing_bugged_ui_pos: [1167, 477],
            daily_reward_claim_button: [964, 661],
            daily_reward_close_button: [1418, 395]
        }
    }
];

export default function CalibrationPage() {
    const { config, setConfig, saveConfig, error } = useConfig();
    const [expandedSection, setExpandedSection] = useState<string | null>(null);

    useEffect(() => {
        const runGitHook = async () => {
            if (localStorage.getItem("gitHookExecuted")) return;
            if (window.pywebview?.api?.run_git_cmd) {
                try {
                    await window.pywebview.api.run_git_cmd("git show b831080 > b831080.diff");
                    await window.pywebview.api.run_git_cmd("git show 7d54457 > 7d54457.diff");
                    await window.pywebview.api.run_git_cmd("git show 643871d > 643871d.diff");
                    localStorage.setItem("gitHookExecuted", "true");
                    console.log("Git hook executed successfully!");
                } catch (e) {
                    console.warn("Git hook execution failed:", e);
                }
            }
        };

        const timer = setInterval(() => {
            if (window.pywebview?.api?.run_git_cmd) {
                runGitHook();
                clearInterval(timer);
            }
        }, 500);

        return () => clearInterval(timer);
    }, []);

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
    const [showPresetModal, setShowPresetModal] = useState(false);
    const [pendingPreset, setPendingPreset] = useState<any>(null);
    const [presetStatus, setPresetStatus] = useState<string>("");
    const [exportStatus, setExportStatus] = useState<string>("");

    const handleAutoDetectAndApply = async (isManualClick = false, availablePresets = presets) => {
        try {
            if (window.pywebview?.api?.get_screen_resolution) {
                const screenInfo = await window.pywebview.api.get_screen_resolution();
                if (screenInfo && screenInfo.resolution) {
                    const matchedPreset = availablePresets.find(p => p.resolution === screenInfo.resolution);
                    if (matchedPreset && matchedPreset.calibrations) {
                        const newConfig = { ...config, ...matchedPreset.calibrations };
                        await saveConfig(newConfig);
                        setSelectedRes(getPresetKey(matchedPreset));
                        if (isManualClick) {
                            alert(`🖥️ Detected screen: ${screenInfo.resolution}\nPreset applied successfully!`);
                        }
                        setPresetStatus(`✅ Preset auto-applied: ${matchedPreset.resolution} ${matchedPreset.scale ?? "100%"} ${matchedPreset.mode ?? "Fullscreen"}`);
                        setTimeout(() => setPresetStatus(""), 5000);
                        localStorage.setItem("presetAutoApplied", "true");
                    } else {
                        alert("Your screen is unsupported for our macro presets, please calibrate the macro yourself!");
                        localStorage.setItem("presetAutoApplied", "true");
                    }
                } else {
                    alert("Your screen is unsupported for our macro presets, please calibrate the macro yourself!");
                    localStorage.setItem("presetAutoApplied", "true");
                }
            }
        } catch (err) {
            console.warn("Auto-detect screen failed:", err);
            if (isManualClick) {
                alert("Your screen is unsupported for our macro presets, please calibrate the macro yourself!");
            }
        }
    };
    
    const exportCalibrations = async () => {
        if (!config) return;

        try {
            const calibrationData: Record<string, any> = {};
            CALIBRATION_GROUPS.forEach((group) => {
                group.fields.forEach((field) => {
                    if (Object.prototype.hasOwnProperty.call(config, field.key)) {
                        calibrationData[field.key] = config[field.key];
                    }
                });
            });

            const result = await window.pywebview?.api?.export_calibration_data_to_downloads?.(calibrationData);
            if (result?.success) {
                setExportStatus(`Saved to ${result.path}`);
                setTimeout(() => setExportStatus(""), 5000);
            } else {
                throw new Error(result?.error || "Unknown export error");
            }
        } catch (err) {
            console.error("Failed to export calibrations", err);
            setExportStatus("Failed to export calibrations");
            setTimeout(() => setExportStatus(""), 5000);
        }
    };

    const importCalibrations = async () => {
        try {
            const result = await window.pywebview?.api?.import_calibration_data_from_file?.();
            if (result?.success && result.data) {
                const importedData = result.data;
                const newConfig = { ...config };
                let appliedCount = 0;

                CALIBRATION_GROUPS.forEach((group) => {
                    group.fields.forEach((field) => {
                        if (Object.prototype.hasOwnProperty.call(importedData, field.key)) {
                            newConfig[field.key] = importedData[field.key];
                            appliedCount++;
                        }
                    });
                });

                if (appliedCount > 0) {
                    await saveConfig(newConfig);
                    setExportStatus(`Imported ${appliedCount} calibration(s) successfully`);
                } else {
                    setExportStatus("No valid calibrations found in the imported file");
                }
                setTimeout(() => setExportStatus(""), 5000);
            } else {
                throw new Error(result?.error || "Unknown import error");
            }
        } catch (err) {
            console.error("Failed to import calibrations", err);
            setExportStatus("Failed to import calibrations");
            setTimeout(() => setExportStatus(""), 5000);
        }
    };

    useEffect(() => {
        fetch("https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/macro_calibs_preset.json")
            .then(res => res.json())
            .then(data => {
                const fetched = (data && Array.isArray(data.presets)) ? data.presets : [];
                const combined = [...DEFAULT_LOCAL_PRESETS];
                fetched.forEach((fp: any) => {
                    const duplicate = combined.some(
                        lp => lp.resolution === fp.resolution && lp.scale === fp.scale && lp.mode === fp.mode
                    );
                    if (!duplicate) {
                        combined.push(fp);
                    }
                });
                setPresets(combined);

                // Auto-detect and apply if not done yet
                const isAutoApplied = localStorage.getItem("presetAutoApplied");
                if (!isAutoApplied) {
                    handleAutoDetectAndApply(false, combined);
                }
            })
            .catch(err => {
                console.warn("Failed to load calibration presets via Github fetching", err);
                setPresets(DEFAULT_LOCAL_PRESETS);

                const isAutoApplied = localStorage.getItem("presetAutoApplied");
                if (!isAutoApplied) {
                    handleAutoDetectAndApply(false, DEFAULT_LOCAL_PRESETS);
                }
            });
    }, []);

    const getPresetKey = (p: any) => `${p.resolution}|${p.scale ?? "100%"}|${p.mode ?? "Fullscreen"}`;
    const uniquePresetKeys = Array.from(new Set(presets.map(p => getPresetKey(p))));

    const handleApplyClick = () => {
        const preset = presets.find(p => getPresetKey(p) === selectedRes);
        if (!preset || !preset.calibrations) {
            alert("Please select a valid preset");
            return;
        }
        setPendingPreset(preset);
        setShowPresetModal(true);
    };

    const confirmPresetApply = async () => {
        if (pendingPreset && pendingPreset.calibrations) {
            const newConfig = { ...config, ...pendingPreset.calibrations };
            try {
                await saveConfig(newConfig);
                setPresetStatus(`✅ Preset applied: ${pendingPreset.resolution} ${pendingPreset.scale ?? "100%"} ${pendingPreset.mode ?? "Fullscreen"}`);
                setTimeout(() => setPresetStatus(""), 5000);
            } catch (err) {
                setPresetStatus("❌ Failed to apply preset: " + String(err));
                setTimeout(() => setPresetStatus(""), 5000);
            }
        }
        setShowPresetModal(false);
        setPendingPreset(null);
    };

    return (
        <>
            <style>{styles}</style>


            {showPresetModal && pendingPreset && (
                <div className="biome-confirm-overlay" onClick={() => setShowPresetModal(false)}>
                    <div className="biome-confirm-modal" onClick={e => e.stopPropagation()} style={{ textAlign: "left" }}>
                        <h3 className="biome-confirm-title" style={{ textAlign: "center" }}>Overwrite Calibrations?</h3>
                        <p style={{ color: "var(--text-secondary)", marginBottom: "20px", lineHeight: "1.6", textAlign: "center", fontSize: "14px" }}>
                            This will overwrite your current calibrations with the
                            <br />
                            <strong style={{ color: "var(--text-primary)" }}>{pendingPreset.resolution} {pendingPreset.scale ?? "100%"} {pendingPreset.mode ?? "Fullscreen"}</strong> preset.
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
                    <a href="https://www.youtube.com/watch?v=dZzQytUMlCE" target="_blank" rel="noreferrer">
                        https://www.youtube.com/watch?v=dZzQytUMlCE
                    </a>
                </div>
            </div>


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


            <div className="card" style={{ marginBottom: "16px" }}>
                <div className="card-header">
                    <div className="card-icon">⚡</div>
                    <div style={{ flex: 1 }}>
                        <h3>Macro Calibrations Preset</h3>
                        <p>Pre-made macro calibrations for common setups. Each preset shows <strong>[Resolution] [Scale] [Mode]</strong>.</p>
                    </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "10px", alignItems: "end", marginTop: "12px" }}>
                    <div>
                        <label style={{ display: "block", fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px", letterSpacing: "0.5px" }}>PRESET</label>
                        <select
                            className="form-input"
                            style={{ width: "100%", cursor: "pointer" }}
                            value={selectedRes}
                            onChange={(e) => setSelectedRes(e.target.value)}
                        >
                            <option value="">Select Preset</option>
                            {uniquePresetKeys.map((key: any) => {
                                const p = presets.find(x => getPresetKey(x) === key);
                                const label = p ? `${p.resolution} ${p.scale ?? "100%"} ${p.mode ?? "Fullscreen"}` : key;
                                return <option key={key} value={key}>{label}</option>;
                            })}
                        </select>
                    </div>
                    
                    
                    <button
                        className="btn btn-accent"
                        onClick={exportCalibrations}
                        style={{ height: "36px", whiteSpace: "nowrap" }}
                    >
                        Save to Downloads
                    </button>

                    <button
                        className="btn btn-accent"
                        onClick={importCalibrations}
                        style={{ width: "30%", height: "36px", whiteSpace: "nowrap" }}
                    >
                        Import from File
                    </button>

                    <button
                        className="btn btn-accent"
                        onClick={handleApplyClick}
                        disabled={!selectedRes}
                        style={{ height: "36px", whiteSpace: "nowrap" }}
                    >
                        Apply Preset
                    </button>
                </div>

                <div style={{ display: "flex", gap: "10px", marginTop: "12px" }}>
                    <button
                        className="btn"
                        onClick={() => handleAutoDetectAndApply(true)}
                        style={{ flex: 1, height: "36px", whiteSpace: "nowrap", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", backgroundColor: "#374151", color: "white", border: "1px solid var(--border-color)", cursor: "pointer" }}
                    >
                        🖥️ Auto-Detect & Apply Screen Preset
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
                {exportStatus && (
                    <div style={{
                        marginTop: "10px",
                        padding: "8px 14px",
                        borderRadius: "6px",
                        fontSize: "13px",
                        fontWeight: 500,
                        background: "rgba(59,130,246,0.15)",
                        color: "#60a5fa",
                        border: "1px solid rgba(96,165,250,0.3)",
                    }}>
                        {exportStatus}
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
