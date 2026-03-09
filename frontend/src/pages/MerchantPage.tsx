import { useConfig } from "../contexts/ConfigContext";
import ToggleSwitch from "../components/ToggleSwitch";
import { useEffect, useState } from "react";

interface MerchantItem {
    name: string;
    enabled: boolean;
    amount: number;
    stopAfterBuy: boolean; // mapped from 3rd boolean in array
}

// Helper to parse config object to array
const parseItems = (itemsObj: any): MerchantItem[] => {
    if (!itemsObj) return [];
    return Object.entries(itemsObj).map(([name, val]: [string, any]) => ({
        name,
        enabled: val[0],
        amount: val[1],
        stopAfterBuy: val[2]
    }));
};

// Helper to convert array back to config object
const serializeItems = (items: MerchantItem[]): any => {
    const obj: any = {};
    items.forEach(item => {
        obj[item.name] = [item.enabled, item.amount, item.stopAfterBuy];
    });
    return obj;
};

function ItemTable({ items, onChange, accent }: {
    items: MerchantItem[];
    onChange: (items: MerchantItem[]) => void;
    accent: string;
}) {
    const toggle = (i: number, key: "enabled" | "stopAfterBuy") => {
        const next = [...items];
        next[i] = { ...next[i], [key]: !next[i][key] };
        onChange(next);
    };
    const setAmount = (i: number, val: string) => {
        const next = [...items];
        const n = parseInt(val) || 1;
        next[i] = { ...next[i], amount: Math.max(1, n) };
        onChange(next);
    };

    return (
        <div className="item-table">
            <div className="item-table-header">
                <span className="item-col-name">Item Name</span>
                <span className="item-col-amount">Amount</span>
                <span className="item-col-rebuy">Rebuy</span>
            </div>
            {items.map((item, i) => (
                <div key={item.name} className={`item-table-row ${item.enabled ? "item-row-active" : ""}`}>
                    <label className="item-col-name item-checkbox-label">
                        <input
                            type="checkbox"
                            checked={item.enabled}
                            onChange={() => toggle(i, "enabled")}
                            className="item-checkbox"
                            style={{ accentColor: accent }}
                        />
                        <span>{item.name}</span>
                    </label>
                    <input
                        type="number"
                        className="item-amount-input"
                        value={item.amount}
                        min={1}
                        onChange={(e) => setAmount(i, e.target.value)}
                    />
                    <label className="item-col-rebuy" title="Stop macro after buying?">
                        <input
                            type="checkbox"
                            checked={item.stopAfterBuy}
                            onChange={() => toggle(i, "stopAfterBuy")}
                            className="item-checkbox"
                            style={{ accentColor: accent }}
                        />
                    </label>
                </div>
            ))}
        </div>
    );
}

export default function MerchantPage() {
    const { config, saveConfig, error } = useConfig();

    // Local state for items to avoid jitter, sync on change
    const [mariItems, setMariItems] = useState<MerchantItem[]>([]);
    const [jesterItems, setJesterItems] = useState<MerchantItem[]>([]);
    const [rinItems, setRinItems] = useState<MerchantItem[]>([]);

    // Collapsible states (default collapsed for faster scrolling)
    const [mariOpen, setMariOpen] = useState(false);
    const [jesterOpen, setJesterOpen] = useState(false);
    const [rinOpen, setRinOpen] = useState(false);

    useEffect(() => {
        if (config) {
            setMariItems(parseItems(config.Mari_Items));
            setJesterItems(parseItems(config.Jester_Items));
            const rinDefaults = [
                "Sunstone Talisman",
                "Moonstone Talisman",
                "Day and Night Talisman",
                "Overtime Talisman",
                "Soul Collector's Talisman",
                "Soul Master's Talisman"
            ];

            let loadedRin = parseItems(config.Rin_Items);
            rinDefaults.forEach(name => {
                if (!loadedRin.find(i => i.name === name)) {
                    loadedRin.push({ name, enabled: false, amount: 1, stopAfterBuy: false });
                }
            });
            setRinItems(loadedRin);
        }
    }, [config]);

    if (error) return <div style={{ padding: "20px", color: "red" }}>Error: {error}</div>;
    if (!config) return <div style={{ padding: "20px" }}>Loading...</div>;

    const updateConfig = (key: string, value: any) => {
        saveConfig({ ...config, [key]: value });
    };

    const handleMariChange = (items: MerchantItem[]) => {
        setMariItems(items);
        updateConfig("Mari_Items", serializeItems(items));
    };

    const handleJesterChange = (items: MerchantItem[]) => {
        setJesterItems(items);
        updateConfig("Jester_Items", serializeItems(items));
    };

    const handleRinChange = (items: MerchantItem[]) => {
        setRinItems(items);
        updateConfig("Rin_Items", serializeItems(items));
    };

    return (
        <>
            <div className="page-header">
                <h2>Merchant</h2>
                <p>Configure merchant detection and auto-purchase settings</p>
            </div>

            {/* Merchant Settings */}
            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🏪</div>
                    <div>
                        <h3>Merchant Teleporter</h3>
                        <p>Auto-use merchant teleporter to find merchants</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Enable Auto Merchant (requires merchant teleporter)"
                    description="Use merchant teleporter item periodically"
                    checked={config.merchant_teleporter || false}
                    onChange={(val) => updateConfig("merchant_teleporter", val)}
                />
                {config.merchant_teleporter && (
                    <div className="duration-input" style={{ marginTop: "6px", marginBottom: "10px" }}>
                        <label className="form-label">Usage Duration:</label>
                        <input
                            className="form-input"
                            value={config.mt_duration || "1"}
                            onChange={(e) => updateConfig("mt_duration", e.target.value)}
                        />
                        <span className="unit">min</span>
                    </div>
                )}

                <ToggleSwitch
                    label="Auto Merchant in Limbo"
                    description="Automatically interact with merchants in Limbo"
                    checked={config.auto_merchant_in_limbo || false}
                    onChange={(val) => updateConfig("auto_merchant_in_limbo", val)}
                />

                <div className="form-row" style={{ marginTop: "10px" }}>
                    <div className="form-group">
                        <label className="form-label">Merchant item extra slot</label>
                        <p className="form-hint">Extra slot if your mouse missed / cannot reach merchant's 5th slot</p>
                        <input
                            className="form-input"
                            value={config.merchant_extra_slot || "0"}
                            onChange={(e) => updateConfig("merchant_extra_slot", e.target.value)}
                            style={{ width: "70px" }}
                        />
                    </div>
                </div>
            </div>

            {/* Ping Settings */}
            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🔔</div>
                    <div>
                        <h3>Discord Pings</h3>
                        <p>Get notified when merchants are found</p>
                    </div>
                </div>

                <ToggleSwitch
                    label="Ping if Mari found?"
                    description="Custom Ping UserID/RoleID"
                    checked={config.ping_mari || false}
                    onChange={(val) => updateConfig("ping_mari", val)}
                />
                {config.ping_mari && (
                    <div className="form-group" style={{ marginTop: "6px", marginBottom: "10px" }}>
                        <label className="form-label">UserID / RoleID</label>
                        <input
                            className="form-input"
                            value={config.mari_user_id || ""}
                            onChange={(e) => updateConfig("mari_user_id", e.target.value)}
                            placeholder="123456789012345678"
                            style={{ width: "240px" }}
                        />
                    </div>
                )}

                <ToggleSwitch
                    label="Ping if Jester found?"
                    description="Custom Ping UserID/RoleID"
                    checked={config.ping_jester || false}
                    onChange={(val) => updateConfig("ping_jester", val)}
                />
                {config.ping_jester && (
                    <div className="form-group" style={{ marginTop: "6px", marginBottom: "10px" }}>
                        <label className="form-label">UserID / RoleID</label>
                        <input
                            className="form-input"
                            value={config.jester_user_id || ""}
                            onChange={(e) => updateConfig("jester_user_id", e.target.value)}
                            placeholder="123456789012345678"
                            style={{ width: "240px" }}
                        />
                    </div>
                )}

                <ToggleSwitch
                    label="Ping if Rin found?"
                    description="Custom Ping UserID/RoleID"
                    checked={config.ping_rin || false}
                    onChange={(val) => updateConfig("ping_rin", val)}
                />
                {config.ping_rin && (
                    <div className="form-group" style={{ marginTop: "6px", marginBottom: "10px" }}>
                        <label className="form-label">UserID / RoleID</label>
                        <input
                            className="form-input"
                            value={config.rin_user_id || ""}
                            onChange={(e) => updateConfig("rin_user_id", e.target.value)}
                            placeholder="123456789012345678"
                            style={{ width: "240px" }}
                        />
                    </div>
                )}
            </div>

            {/* Mari stuff*/}
            <div className="card">
                <div
                    className="card-header"
                    onClick={() => setMariOpen(!mariOpen)}
                    style={{ cursor: "pointer", userSelect: "none" }}
                    title="Click to toggle"
                >
                    <div className="card-icon">🎒</div>
                    <div style={{ flexGrow: 1 }}>
                        <h3>Mari Item Settings</h3>
                        <p>Select items to auto-purchase from Mari</p>
                    </div>
                    <div style={{ fontSize: "1.2rem", color: "var(--text-secondary)", transform: mariOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                        ▼
                    </div>
                </div>
                {mariOpen && <ItemTable items={mariItems} onChange={handleMariChange} accent="#7c5bf5" />}
            </div>

            {/* Jester stuffs */}
            <div className="card">
                <div
                    className="card-header"
                    onClick={() => setJesterOpen(!jesterOpen)}
                    style={{ cursor: "pointer", userSelect: "none" }}
                    title="Click to toggle"
                >
                    <div className="card-icon">🃏</div>
                    <div style={{ flexGrow: 1 }}>
                        <h3>Jester Item Settings</h3>
                        <p>Select items to auto-purchase from Jester</p>
                    </div>
                    <div style={{ fontSize: "1.2rem", color: "var(--text-secondary)", transform: jesterOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                        ▼
                    </div>
                </div>
                {jesterOpen && <ItemTable items={jesterItems} onChange={handleJesterChange} accent="#f59e0b" />}
            </div>

            {/* Rin stuff*/}
            <div className="card">
                <div
                    className="card-header"
                    onClick={() => setRinOpen(!rinOpen)}
                    style={{ cursor: "pointer", userSelect: "none" }}
                    title="Click to toggle"
                >
                    <div className="card-icon">🦊</div>
                    <div style={{ flexGrow: 1 }}>
                        <h3>Rin Item Settings</h3>
                        <p>Select items to auto-purchase from Rin</p>
                    </div>
                    <div style={{ fontSize: "1.2rem", color: "var(--text-secondary)", transform: rinOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>
                        ▼
                    </div>
                </div>
                {rinOpen && <ItemTable items={rinItems} onChange={handleRinChange} accent="#06b6d4" />}
            </div>
        </>
    );
}
