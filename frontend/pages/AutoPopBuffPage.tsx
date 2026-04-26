import { useState } from "react";
import { useConfig } from "../contexts/ConfigContext";

type BuffSelection = [boolean, number];
type BuffConfig = Record<string, BuffSelection>;
type AutoPopBiomeEntry = {
    enabled: boolean;
    buffs: BuffConfig;
};
type AutoPopBiomeMap = Record<string, AutoPopBiomeEntry>;

const RARE_BIOMES = ["GLITCHED", "DREAMSPACE", "CYBERSPACE"];
const DEFAULT_BUFFS = [
    "Fortune Potion I",
    "Fortune Potion II",
    "Fortune Potion III",
    "Godlike Potion",
    "Haste Potion I",
    "Haste Potion II",
    "Haste Potion III",
    "Heavenly Potion",
    "Lucky Potion",
    "Oblivion Potion",
    "Potion of bound",
    "Speed Potion",
    "Stella's Candle",
    "Strange Potion I",
    "Strange Potion II",
    "Transcendent Potion",
    "Warp Potion",
    "Xyz Potion",
];
const FALLBACK_BIOME_COLORS: Record<string, string> = {
    WINDY: "#9ae5ff",
    RAINY: "#027cbd",
    SNOWY: "#dceff9",
    "SAND STORM": "#8f7057",
    HELL: "#ff4719",
    STARFALL: "#011ab7",
    CORRUPTION: "#6d32a8",
    NULL: "#838383",
    GLITCHED: "#bfff00",
    DREAMSPACE: "#ea9dda",
    CYBERSPACE: "#0a1a3d",
    AURORA: "#56d6a0",
    HEAVEN: "#dfaf63",
};

function normalizeColor(value: string | undefined): string {
    if (!value) return "#9ca3af";
    return value.startsWith("0x") ? `#${value.slice(2)}` : value;
}

function normalizeBuffConfig(raw: unknown): BuffConfig {
    const normalized: BuffConfig = {};
    for (const buffName of DEFAULT_BUFFS) {
        normalized[buffName] = [false, 1];
    }

    if (!raw || typeof raw !== "object") {
        return normalized;
    }

    for (const [buffName, buffValue] of Object.entries(raw as Record<string, unknown>)) {
        let enabled = false;
        let amount = 1;

        if (Array.isArray(buffValue)) {
            enabled = Boolean(buffValue[0]);
            amount = Math.max(1, Number(buffValue[1]) || 1);
        }

        normalized[buffName] = [enabled, amount];
    }

    return normalized;
}

function getAutoPopBiomes(config: Record<string, unknown>): AutoPopBiomeMap {
    const raw = config.auto_pop_biomes;
    if (!raw || typeof raw !== "object") {
        return {};
    }

    const normalized: AutoPopBiomeMap = {};
    for (const [biomeName, entry] of Object.entries(raw as Record<string, unknown>)) {
        const rawEntry = entry && typeof entry === "object" ? entry as Record<string, unknown> : {};
        normalized[biomeName] = {
            enabled: Boolean(rawEntry.enabled),
            buffs: normalizeBuffConfig(rawEntry.buffs),
        };
    }

    return normalized;
}

function getBiomeNames(config: Record<string, unknown>, autoPopBiomes: AutoPopBiomeMap): string[] {
    const names = new Set<string>();

    for (const biomeName of Object.keys(autoPopBiomes)) {
        if (biomeName && biomeName !== "NORMAL") {
            names.add(biomeName);
        }
    }

    const biomeCounts = config.biome_counts;
    if (biomeCounts && typeof biomeCounts === "object") {
        for (const biomeName of Object.keys(biomeCounts as Record<string, unknown>)) {
            if (biomeName && biomeName !== "NORMAL") {
                names.add(biomeName);
            }
        }
    }

    const biomeNotifier = config.biome_notifier;
    if (biomeNotifier && typeof biomeNotifier === "object") {
        for (const biomeName of Object.keys(biomeNotifier as Record<string, unknown>)) {
            if (biomeName && biomeName !== "NORMAL") {
                names.add(biomeName);
            }
        }
    }

    const orderedRare = RARE_BIOMES.filter((biomeName) => names.has(biomeName));
    const orderedOther = [...names].filter((biomeName) => !RARE_BIOMES.includes(biomeName)).sort();
    return [...orderedRare, ...orderedOther];
}

function getBiomeEntry(autoPopBiomes: AutoPopBiomeMap, biomeName: string): AutoPopBiomeEntry {
    return autoPopBiomes[biomeName] ?? {
        enabled: false,
        buffs: normalizeBuffConfig(undefined),
    };
}

function countEnabledBuffs(buffs: BuffConfig): number {
    return Object.values(buffs).filter(([enabled]) => enabled).length;
}

function getBiomeColor(config: Record<string, unknown>, biomeName: string): string {
    const overrides = config.custom_biome_overrides;
    if (overrides && typeof overrides === "object") {
        const biomeOverride = (overrides as Record<string, { color?: string }>)[biomeName];
        if (biomeOverride?.color) {
            return normalizeColor(biomeOverride.color);
        }
    }

    return FALLBACK_BIOME_COLORS[biomeName] ?? "#9ca3af";
}

export default function AutoPopBuffPage() {
    const { config, saveConfig, error } = useConfig();
    const [selectedBiome, setSelectedBiome] = useState<string | null>(null);

    if (error) {
        return (
            <div style={{ padding: "20px", color: "#ef4444" }}>
                <h3>Error Loading Settings</h3>
                <p>{error}</p>
            </div>
        );
    }

    if (!config) {
        return <div style={{ padding: "20px" }}>Loading auto pop buff settings...</div>;
    }

    const typedConfig = config as Record<string, unknown>;
    const autoPopBiomes = getAutoPopBiomes(typedConfig);
    const biomeNames = getBiomeNames(typedConfig, autoPopBiomes);
    const rareBiomes = biomeNames.filter((biomeName) => RARE_BIOMES.includes(biomeName));
    const otherBiomes = biomeNames.filter((biomeName) => !RARE_BIOMES.includes(biomeName));
    const activeBiomeEntry = selectedBiome ? getBiomeEntry(autoPopBiomes, selectedBiome) : null;

    const saveAutoPopBiomes = (nextBiomes: AutoPopBiomeMap) => {
        saveConfig({
            ...config,
            auto_pop_biomes: nextBiomes,
        });
    };

    const updateBiomeEnabled = (biomeName: string, enabled: boolean) => {
        const currentEntry = getBiomeEntry(autoPopBiomes, biomeName);
        saveAutoPopBiomes({
            ...autoPopBiomes,
            [biomeName]: {
                ...currentEntry,
                enabled,
            },
        });
    };

    const updateBuffSelection = (biomeName: string, buffName: string, field: "enabled" | "amount", value: boolean | string) => {
        const currentEntry = getBiomeEntry(autoPopBiomes, biomeName);
        const nextBuffs = {
            ...currentEntry.buffs,
        };
        const currentBuff = nextBuffs[buffName] ?? [false, 1];
        nextBuffs[buffName] = field === "enabled"
            ? [Boolean(value), currentBuff[1]]
            : [currentBuff[0], Math.max(1, Number(value) || 1)];

        saveAutoPopBiomes({
            ...autoPopBiomes,
            [biomeName]: {
                ...currentEntry,
                buffs: nextBuffs,
            },
        });
    };

    const renderBiomeRows = (title: string, biomes: string[]) => {
        if (!biomes.length) {
            return null;
        }

        return (
            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🧪</div>
                    <div>
                        <h3>{title}</h3>
                        <p>Enable exact biome triggers and configure a separate buff loadout for each one</p>
                    </div>
                </div>

                <div style={{ display: "grid", gap: "10px" }}>
                    {biomes.map((biomeName) => {
                        const biomeEntry = getBiomeEntry(autoPopBiomes, biomeName);
                        const enabledBuffs = countEnabledBuffs(biomeEntry.buffs);
                        const biomeColor = getBiomeColor(typedConfig, biomeName);

                        return (
                            <div
                                key={biomeName}
                                style={{
                                    display: "grid",
                                    gridTemplateColumns: "1fr auto auto",
                                    gap: "12px",
                                    alignItems: "center",
                                    padding: "12px 14px",
                                    border: "1px solid var(--border-color)",
                                    background: biomeEntry.enabled ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.02)",
                                }}
                            >
                                <div>
                                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                                        <span style={{ width: "10px", height: "10px", borderRadius: "999px", background: biomeColor }} />
                                        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{biomeName}</span>
                                    </div>
                                    <div className="form-hint">
                                        {enabledBuffs > 0 ? `${enabledBuffs} buff${enabledBuffs === 1 ? "" : "s"} selected` : "No buffs selected yet"}
                                    </div>
                                </div>

                                <button
                                    className="btn btn-secondary"
                                    style={{ whiteSpace: "nowrap" }}
                                    onClick={() => setSelectedBiome(biomeName)}
                                >
                                    Buff Selection
                                </button>

                                <label style={{ display: "flex", alignItems: "center", gap: "8px", whiteSpace: "nowrap", color: "var(--text-secondary)" }}>
                                    <input
                                        type="checkbox"
                                        checked={biomeEntry.enabled}
                                        onChange={(event) => updateBiomeEnabled(biomeName, event.target.checked)}
                                        style={{ width: "16px", height: "16px" }}
                                    />
                                    Enable
                                </label>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    };

    return (
        <>
            {selectedBiome && activeBiomeEntry && (
                <div
                    className="modal-overlay"
                    style={{
                        position: "fixed",
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: "rgba(0,0,0,0.72)",
                        zIndex: 1000,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                    }}
                >
                    <div
                        className="modal-content"
                        style={{
                            backgroundColor: "var(--bg-card)",
                            padding: "22px",
                            width: "760px",
                            maxHeight: "84vh",
                            overflowY: "auto",
                            border: "1px solid var(--border-color)",
                            boxShadow: "0 10px 30px rgba(0,0,0,0.45)",
                        }}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", marginBottom: "18px" }}>
                            <div>
                                <h3 style={{ margin: 0 }}>{selectedBiome} Buff Selection</h3>
                                <p style={{ margin: "6px 0 0 0", color: "var(--text-secondary)", fontSize: "13px" }}>
                                    Only the enabled buffs below will be used when auto pop triggers in this biome.
                                </p>
                            </div>
                            <button className="btn btn-secondary" onClick={() => setSelectedBiome(null)}>Close</button>
                        </div>

                        <div className="buff-grid">
                            {Object.keys(activeBiomeEntry.buffs).map((buffName) => {
                                const [enabled, amount] = activeBiomeEntry.buffs[buffName] ?? [false, 1];
                                return (
                                    <div key={buffName} className="buff-item">
                                        <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                            <input
                                                type="checkbox"
                                                checked={enabled}
                                                onChange={(event) => updateBuffSelection(selectedBiome, buffName, "enabled", event.target.checked)}
                                            />
                                            <span className="buff-name">{buffName}</span>
                                        </label>
                                        <input
                                            className="form-input buff-amount"
                                            type="number"
                                            min="1"
                                            value={amount}
                                            onChange={(event) => updateBuffSelection(selectedBiome, buffName, "amount", event.target.value)}
                                        />
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            <div className="page-header">
                <h2>Auto Pop Buff</h2>
                <p>Use separate biome-specific buff loadouts instead of the old rare-vs-normal grouping</p>
            </div>

            <div className="info-banner" style={{ marginBottom: "16px" }}>
                Auto Pop Buff now interrupts fishing flows, waits 0.3 seconds, uses the selected buffs for the exact biome you enabled, then lets fishing continue. Fishing failsafe rejoin is deferred until rare biomes end.
            </div>

            {renderBiomeRows("Rare Biomes", rareBiomes)}
            {renderBiomeRows("Other Biomes", otherBiomes)}
        </>
    );
}