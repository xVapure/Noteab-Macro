import { useEffect, useState } from "react";
import ToggleSwitch from "../components/ToggleSwitch";
import { useConfig } from "../contexts/ConfigContext";

export default function MiscPage() {
    const { config, saveConfig, error } = useConfig();
    const [calibrationTarget, setCalibrationTarget] = useState<"ocr" | "reconnect" | null>(null);

    useEffect(() => {
        (window as any).onCalibrationResultMisc = (data: any) => {
            if (!calibrationTarget || !config) return;

            let nextValue: number[] | null = null;
            if (calibrationTarget === "ocr") {
                if (Array.isArray(data?.value) && data?.key === "first_item_slot_ocr_pos") {
                    const candidate = data.value.slice(0, 4).map((value: any) => Math.round(Number(value)));
                    if (candidate.length === 4 && candidate.every((value: number) => Number.isFinite(value)) && candidate[2] > 0 && candidate[3] > 0) {
                        nextValue = candidate;
                    }
                } else if (data?.w !== undefined) {
                    const candidate = [Math.round(Number(data.x)), Math.round(Number(data.y)), Math.round(Number(data.w)), Math.round(Number(data.h))];
                    if (candidate.every((value) => Number.isFinite(value)) && candidate[2] > 0 && candidate[3] > 0) {
                        nextValue = candidate;
                    }
                }
            } else if (calibrationTarget === "reconnect") {
                if (Array.isArray(data?.value) && data?.key === "reconnect_start_button") {
                    const candidate = data.value.slice(0, 2).map((value: any) => Math.round(Number(value)));
                    if (candidate.length === 2 && candidate.every((value: number) => Number.isFinite(value))) {
                        nextValue = candidate;
                    }
                } else if (data?.x !== undefined && data?.y !== undefined && data?.w === undefined && data?.h === undefined) {
                    const candidate = [Math.round(Number(data.x)), Math.round(Number(data.y))];
                    if (candidate.every((value) => Number.isFinite(value))) {
                        nextValue = candidate;
                    }
                }
            }

            if (!nextValue) return;

            if (calibrationTarget === "ocr") {
                saveConfig({ ...config, first_item_slot_ocr_pos: nextValue });
            } else {
                saveConfig({ ...config, reconnect_start_button: nextValue });
            }

            setCalibrationTarget(null);
        };

        return () => {
            delete (window as any).onCalibrationResultMisc;
        };
    }, [calibrationTarget, config, saveConfig]);

    if (error) {
        return (
            <div style={{ padding: "20px", color: "#ef4444" }}>
                <h3>Error Loading Settings</h3>
                <p>{error}</p>
            </div>
        );
    }

    if (!config) {
        return <div style={{ padding: "20px" }}>Loading settings...</div>;
    }

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    const startOCRCalibration = async () => {
        setCalibrationTarget("ocr");
        try {
            if (window.pywebview?.api) {
                await window.pywebview.api.create_calibration_window("first_item_slot_ocr_pos", "region");
            }
        } catch (errorValue) {
            console.error("Failed to open calibration window", errorValue);
            alert("Failed to open calibration tool: " + errorValue);
            setCalibrationTarget(null);
        }
    };

    const startReconnectCalibration = async () => {
        setCalibrationTarget("reconnect");
        try {
            if (window.pywebview?.api) {
                await window.pywebview.api.create_calibration_window("reconnect_start_button", "point");
            }
        } catch (errorValue) {
            console.error("Failed to open calibration window", errorValue);
            alert("Failed to open calibration tool: " + errorValue);
            setCalibrationTarget(null);
        }
    };

    return (
        <>
            <div className="page-header">
                <h2>Automated Actions</h2>
                <p>General automation, recovery, screenshot, and quest settings</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🎬</div>
                    <div>
                        <h3>Biome Recording</h3>
                        <p>Auto clip and screenshot rare biome detections</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Glitched/Dreamspace Biome clip keybind"
                    description="Require 1 of 2 recorders: Medal, Xbox Gaming Bar"
                    checked={config.record_rare_biome || false}
                    onChange={(value) => updateConfig("record_rare_biome", value)}
                />

                {config.record_rare_biome && (
                    <div className="form-row" style={{ marginTop: "10px" }}>
                        <div className="form-group">
                            <label className="form-label">Record Keybind</label>
                            <input
                                className="form-input"
                                value={config.rare_biome_record_keybind || "F8"}
                                onChange={(event) => updateConfig("rare_biome_record_keybind", event.target.value)}
                                style={{ width: "140px" }}
                            />
                        </div>
                    </div>
                )}

                <ToggleSwitch
                    label="Rare Biomes Screenshot"
                    description="Automatically send a screenshot in your webhook when Glitched, Dreamspace, or Cyberspace is found"
                    checked={config.rare_biome_screenshot !== false}
                    onChange={(value) => updateConfig("rare_biome_screenshot", value)}
                />
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">📦</div>
                    <div>
                        <h3>Item Usage</h3>
                        <p>Configure BR, SC, reconnect, and OCR safeguards</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Biome Randomizer (BR)"
                    checked={config.biome_randomizer || false}
                    onChange={(value) => updateConfig("biome_randomizer", value)}
                />
                {config.biome_randomizer && (
                    <div className="duration-input" style={{ marginBottom: "6px" }}>
                        <label className="form-label">Usage Duration (minutes):</label>
                        <input
                            className="form-input"
                            value={config.br_duration || "36"}
                            onChange={(event) => updateConfig("br_duration", event.target.value)}
                            style={{ width: "70px" }}
                        />
                    </div>
                )}

                <ToggleSwitch
                    label="Strange Controller (SC)"
                    checked={config.strange_controller || false}
                    onChange={(value) => updateConfig("strange_controller", value)}
                />
                {config.strange_controller && (
                    <div className="duration-input" style={{ marginBottom: "6px" }}>
                        <label className="form-label">Usage Duration (minutes):</label>
                        <input
                            className="form-input"
                            value={config.sc_duration || "21"}
                            onChange={(event) => updateConfig("sc_duration", event.target.value)}
                            style={{ width: "70px" }}
                        />
                    </div>
                )}

                <ToggleSwitch
                    label="Auto reconnect to your PS (experimental)"
                    description="When Roblox disconnects, relaunch and rejoin using your private server link."
                    checked={config.auto_reconnect || false}
                    onChange={(value) => updateConfig("auto_reconnect", value)}
                />
                {config.auto_reconnect && (
                    <>
                        <div className="form-hint" style={{ marginTop: "6px", marginBottom: "8px" }}>
                            Supports both private server code links and Roblox share links (for example: /share?code=...&type=Server).
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                            <button
                                className="btn btn-accent"
                                style={{ fontSize: "11px", padding: "6px 12px" }}
                                onClick={startReconnectCalibration}
                            >
                                Join Button in Sol&apos;s RNG Calibration
                            </button>
                            <span className="form-hint">{JSON.stringify(config.reconnect_start_button || [954, 876])}</span>
                        </div>
                    </>
                )}

                <div className="form-group" style={{ marginTop: "10px", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "10px" }}>
                    <label className="form-label">Inventory Mouse Click Delay (milliseconds)</label>
                    <div className="duration-input">
                        <input
                            className="form-input"
                            value={config.inventory_click_delay || "650"}
                            onChange={(event) => updateConfig("inventory_click_delay", event.target.value)}
                            style={{ width: "90px" }}
                        />
                    </div>
                </div>

                <ToggleSwitch
                    label="OCR failsafe"
                    description="Prevent wrong item usage by validating the first inventory slot before clicking Use"
                    checked={config.enable_ocr_failsafe || false}
                    onChange={(value) => updateConfig("enable_ocr_failsafe", value)}
                />
                {config.enable_ocr_failsafe && (
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "6px" }}>
                        <button
                            className="btn btn-accent"
                            style={{ fontSize: "11px", padding: "6px 12px" }}
                            onClick={startOCRCalibration}
                        >
                            OCR Calibration
                        </button>
                        <span className="form-hint">{JSON.stringify(config.first_item_slot_ocr_pos || [797, 410, 98, 97])}</span>
                    </div>
                )}
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">📸</div>
                    <div>
                        <h3>Periodical Screenshots &amp; Quests</h3>
                        <p>Automatically capture screenshots and claim quests on a schedule</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Periodical Aura Screenshot"
                    checked={config.periodical_aura_screenshot || false}
                    onChange={(value) => updateConfig("periodical_aura_screenshot", value)}
                />
                {config.periodical_aura_screenshot && (
                    <div className="duration-input" style={{ marginBottom: "6px" }}>
                        <label className="form-label">Interval (minutes):</label>
                        <input
                            className="form-input"
                            value={config.periodical_aura_interval || "25"}
                            onChange={(event) => updateConfig("periodical_aura_interval", event.target.value)}
                            style={{ width: "70px" }}
                        />
                    </div>
                )}

                <ToggleSwitch
                    label="Periodical Inventory Screenshot"
                    checked={config.periodical_inventory_screenshot || false}
                    onChange={(value) => updateConfig("periodical_inventory_screenshot", value)}
                />
                {config.periodical_inventory_screenshot && (
                    <div className="duration-input" style={{ marginBottom: "6px" }}>
                        <label className="form-label">Inventory Interval (minutes):</label>
                        <input
                            className="form-input"
                            value={config.periodical_inventory_interval || "25"}
                            onChange={(event) => updateConfig("periodical_inventory_interval", event.target.value)}
                            style={{ width: "70px" }}
                        />
                    </div>
                )}

                <ToggleSwitch
                    label="Auto claim daily quests"
                    checked={config.auto_claim_daily_quests || false}
                    onChange={(value) => updateConfig("auto_claim_daily_quests", value)}
                />
                {config.auto_claim_daily_quests && (
                    <div className="duration-input">
                        <label className="form-label">Claim Interval (minutes):</label>
                        <input
                            className="form-input"
                            value={config.auto_claim_interval || "30"}
                            onChange={(event) => updateConfig("auto_claim_interval", event.target.value)}
                            style={{ width: "70px" }}
                        />
                    </div>
                )}
            </div>
        </>
    );
}
