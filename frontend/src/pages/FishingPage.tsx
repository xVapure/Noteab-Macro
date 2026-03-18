import { useConfig } from "../contexts/ConfigContext";
import ToggleSwitch from "../components/ToggleSwitch";

type FishingCalibrationItem = {
    key: string;
    label: string;
    isRegion?: boolean;
    fallback: number[];
};

const FISHING_CALIBRATIONS: FishingCalibrationItem[] = [
    { key: "fishing_detect_pixel", label: "Fishing Detect Pixel", fallback: [1176, 836] },
    { key: "fishing_click_position", label: "Start Fishing Button", fallback: [862, 843] },
    { key: "fishing_midbar_sample_pos", label: "Mid Bar Sample Position", fallback: [955, 767] },
    { key: "fishing_close_button_pos", label: "Fishing Close Button", fallback: [1113, 342] },
    { key: "fishing_bar_region", label: "Fishing Bar Region", isRegion: true, fallback: [757, 762, 405, 21] },
    { key: "fishing_flarg_dialogue_box", label: "Captain Flarg Dialogue Box", fallback: [1046, 782] },
    { key: "fishing_shop_open_button", label: "Open Fishing Shop", fallback: [616, 938] },
    { key: "fishing_shop_sell_tab", label: "Fishing Shop Sell Tab", fallback: [1285, 312] },
    { key: "fishing_shop_close_button", label: "Close Fishing Shop", fallback: [1458, 269] },
    { key: "fishing_shop_first_fish", label: "First Fish In Shop", fallback: [827, 404] },
    { key: "fishing_shop_sell_all_button", label: "Sell All Button", fallback: [662, 799] },
    { key: "fishing_confirm_sell_all_button", label: "Confirm Sell All Button", fallback: [800, 619] },
];

function formatPoint(value: any, fallback: number[]) {
    const arr = Array.isArray(value) ? value : fallback;
    return `[${Number(arr[0]) || 0}, ${Number(arr[1]) || 0}]`;
}

function formatRegion(value: any, fallback: number[]) {
    const arr = Array.isArray(value) ? value : fallback;
    return `[${Number(arr[0]) || 0}, ${Number(arr[1]) || 0}, ${Number(arr[2]) || 0}, ${Number(arr[3]) || 0}]`;
}

export default function FishingPage() {
    const { config, saveConfig, error } = useConfig();

    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    const handleFishingFailsafeToggle = (enabled: boolean) => {
        if (!enabled) {
            updateConfig("fishing_failsafe_rejoin", false);
            return;
        }

        const reconnectEnabled = Boolean(config.auto_reconnect);
        if (!reconnectEnabled) {
            updateConfig("fishing_failsafe_rejoin", false);
            alert("you need to enable reconnect feature for fishing failsafe to work");
            if (typeof (window as any).onNavigateTab === "function") {
                (window as any).onNavigateTab("misc");
            }
            return;
        }

        updateConfig("fishing_failsafe_rejoin", true);
    };

    const fishingMode = config.fishing_mode || false;
    const fishingFailsafe = config.fishing_failsafe_rejoin || false;
    const fishSellingEnabled = config.fishing_enable_selling || false;
    const equipAuraBeforeMovement = config.fishing_equip_aura_before_movement || false;
    const fishingMerchantEnabled = config.fishing_use_merchant_every_x_fish || false;
    const fishingBrScEnabled = config.fishing_use_br_sc_every_x_fish || false;

    const displayAllCalibrationsOnScreen = async () => {
        try {
            if ((window as any).pywebview?.api?.display_all_fishing_calibrations_on_screen) {
                await (window as any).pywebview.api.display_all_fishing_calibrations_on_screen(3500);
            }
        } catch (e) {
            console.error("Failed to display fishing calibrations on screen:", e);
            alert("Failed to display fishing calibrations on screen: " + e);
        }
    };

    return (
        <>
            <div className="page-header">
                <h2>Fishing</h2>
                <p>Run fishing logic while suppressing other automatic feature loops</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🎣</div>
                    <div>
                        <h3>Fishing Mode</h3>
                        <p>When enabled, the macro runs fishing logic and pauses most other automations</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable Fishing Mode"
                    description="Auto Pop Buff still has priority and will interrupt fishing. Remote Control stays enabled."
                    checked={fishingMode}
                    onChange={(val) => updateConfig("fishing_mode", val)}
                />

                <div className="form-row" style={{ marginTop: "8px" }}>
                    <div className="form-group">
                        <label className="form-label">Fishing actions delay (in miliseconds)</label>
                        <input
                            className="form-input"
                            value={config.fishing_actions_delay_ms ?? "100"}
                            onChange={(e) => updateConfig("fishing_actions_delay_ms", e.target.value)}
                            style={{ width: "90px" }}
                        />
                    </div>
                </div>

                <ToggleSwitch
                    label="Fishing failsafe (rejoin if timeout)"
                    description="If no fishing minigame is detected for 60 seconds after the last Start Fishing click, close Roblox so reconnect logic can take over."
                    checked={fishingFailsafe}
                    onChange={handleFishingFailsafeToggle}
                />

                <ToggleSwitch
                    label="Enable fish selling"
                    description="Automatically run fish selling flow after enough catches."
                    checked={fishSellingEnabled}
                    onChange={(val) => updateConfig("fishing_enable_selling", val)}
                />
                {fishSellingEnabled && (
                    <div className="form-row" style={{ marginTop: "8px" }}>
                        <div className="form-group">
                            <label className="form-label">Sell after x fish</label>
                            <input
                                className="form-input"
                                value={config.fishing_sell_after_x_fish ?? "30"}
                                onChange={(e) => updateConfig("fishing_sell_after_x_fish", e.target.value)}
                                style={{ width: "90px" }}
                            />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Sell how many fish</label>
                            <input
                                className="form-input"
                                value={config.fishing_sell_how_many_fish ?? "1"}
                                onChange={(e) => updateConfig("fishing_sell_how_many_fish", e.target.value)}
                                style={{ width: "90px" }}
                            />
                        </div>
                    </div>
                )}

                <ToggleSwitch
                    label="Equip an aura before movement"
                    description="Before walking to fish or sell fish, equip the aura name below using Aura calibration points."
                    checked={equipAuraBeforeMovement}
                    onChange={(val) => updateConfig("fishing_equip_aura_before_movement", val)}
                />
                {equipAuraBeforeMovement && (
                    <div className="form-row" style={{ marginTop: "8px" }}>
                        <div className="form-group">
                            <label className="form-label">Aura name to equip</label>
                            <input
                                className="form-input"
                                value={config.fishing_movement_aura_name || ""}
                                onChange={(e) => updateConfig("fishing_movement_aura_name", e.target.value)}
                                style={{ width: "220px" }}
                                placeholder="Enter aura name"
                            />
                        </div>
                    </div>
                )}

                <ToggleSwitch
                    label="Use merchant teleporter every x fishes"
                    description="Runs full auto-merchant flow directly from fishing mode."
                    checked={fishingMerchantEnabled}
                    onChange={(val) => updateConfig("fishing_use_merchant_every_x_fish", val)}
                />
                {fishingMerchantEnabled && (
                    <div className="form-row" style={{ marginTop: "8px" }}>
                        <div className="form-group">
                            <label className="form-label">Use merchant teleporter every x fish</label>
                            <input
                                className="form-input"
                                value={config.fishing_merchant_every_x_fish ?? "30"}
                                onChange={(e) => updateConfig("fishing_merchant_every_x_fish", e.target.value)}
                                style={{ width: "90px" }}
                            />
                        </div>
                    </div>
                )}

                <ToggleSwitch
                    label="Use BR/SC every x fishes"
                    description="After x fish catches, run BR then SC with the usual OCR failsafe. If multiple flows trigger together, order is: sell -> merchant -> BR/SC."
                    checked={fishingBrScEnabled}
                    onChange={(val) => updateConfig("fishing_use_br_sc_every_x_fish", val)}
                />
                {fishingBrScEnabled && (
                    <div className="form-row" style={{ marginTop: "8px" }}>
                        <div className="form-group">
                            <label className="form-label">Use BR/SC every x fish</label>
                            <input
                                className="form-input"
                                value={config.fishing_br_sc_every_x_fish ?? "30"}
                                onChange={(e) => updateConfig("fishing_br_sc_every_x_fish", e.target.value)}
                                style={{ width: "90px" }}
                            />
                        </div>
                    </div>
                )}

                {fishingMode && (
                    <div className="info-banner" style={{ marginTop: "10px" }}>
                        Fishing mode is active. Movements, potion crafting, periodic screenshots, aura screenshots, daily quest claiming, and other non-essential mouse actions are paused. Fishing auto-merchant can still run if enabled above.
                    </div>
                )}
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">📍</div>
                    <div>
                        <h3>Fishing Calibration Values</h3>
                        <p>Edit these in Macro Calibrations &gt; Fishing Calibration</p>
                    </div>
                </div>

                <div style={{ marginBottom: "12px" }}>
                    <button
                        className="btn btn-sm"
                        style={{ whiteSpace: "nowrap", padding: "6px 12px" }}
                        onClick={displayAllCalibrationsOnScreen}
                    >
                        Display On Screen Calibration
                    </button>
                </div>

                <div className="settings-grid">
                    {FISHING_CALIBRATIONS.map((item) => (
                        <div
                            key={item.key}
                            className="setting-row"
                            style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "center", gap: "8px" }}
                        >
                            <span className="setting-label">{item.label}</span>
                            <code>
                                {item.isRegion
                                    ? formatRegion((config as any)[item.key], item.fallback)
                                    : formatPoint((config as any)[item.key], item.fallback)}
                            </code>
                        </div>
                    ))}
                </div>
            </div>
        </>
    );
}