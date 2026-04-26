import { useState, useCallback } from "react";

interface HeaderBarProps {
    isRunning: boolean;
    onToggle: () => void;
    theme: string;
    onThemeChange: (theme: string) => void;
    isGlitching: boolean;
    setActiveTab?: (tab: string) => void;
}

const themes = [
    { id: "midnight", label: "Midnight" },
    { id: "solar", label: "Solar" },
    { id: "arctic", label: "Arctic" },
    { id: "neon", label: "Neon" },
    { id: "sunset", label: "Sunset" },
    { id: "ocean", label: "Ocean" },
    { id: "forest", label: "Forest" },
    { id: "cyberpunk", label: "Cyberpunk" },
    { id: "lavender", label: "Lavender" },
];

const SEARCH_INDEX = [
    { title: "Webhooks", tab: "webhook", keywords: ["discord", "webhook", "ping", "notification", "role", "server", "glitched", "dreamspace", "cyberspace", "url", "test", "high accuracy", "logs", "username"] },
    { title: "Macro Calibrations", tab: "calibrations", keywords: ["calibrate", "positions", "window", "screen", "resolution", "align", "coordinates"] },
    { title: "Automated actions", tab: "misc", keywords: ["inventory", "delay", "screenshot", "quest", "biome record", "clip", "medal", "rare biome", "ocr failsafe", "biome randomizer", "br", "strange controller", "sc", "reconnect", "private server", "daily", "eden"] },
    { title: "Fishing", tab: "fishing", keywords: ["fish", "rod", "merchant teleporter", "fish failsafe", "sell all", "flarg", "minigame", "idle"] },
    { title: "Merchant", tab: "merchant", keywords: ["merchant", "shop", "potions", "items", "buy", "teleport"] },
    { title: "Auto Pop & Buff", tab: "autopopbuff", keywords: ["auto pop", "buff", "potion", "fortune", "haste", "lucky", "speed", "universe", "heavenly", "oblivion"] },
    { title: "Auras", tab: "auras", keywords: ["aura", "record", "ping", "min rarity", "force", "clip", "user id", "keybind", "test", "global"] },
    { title: "Movements", tab: "movements", keywords: ["move", "walk", "jump", "obby", "macro", "path", "record", "replay", "jump"] },
    { title: "Potion Crafting", tab: "potioncraft", keywords: ["craft", "potion", "cauldron", "stella", "brew", "ingredients"] },
    { title: "Other Features", tab: "otherfeatures", keywords: ["anti", "afk", "idle", "reset character", "glitch effect"] },
    { title: "Remote Access", tab: "remoteaccess", keywords: ["remote", "access", "control", "api", "discord bot"] },
    { title: "Customization", tab: "customization", keywords: ["custom", "background", "image", "theme"] }
];

export default function HeaderBar({ isRunning, onToggle, theme, onThemeChange, isGlitching, setActiveTab }: HeaderBarProps) {
    const [alwaysOnTop, setAlwaysOnTop] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [isSearchFocused, setIsSearchFocused] = useState(false);

    const toggleAlwaysOnTop = async () => {
        const next = !alwaysOnTop;
        try {
            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.set_always_on_top(next);
            }
            setAlwaysOnTop(next);
        } catch { /* browser fallback */ }
    };

    const handleImportConfig = async () => {
        if (isImporting) return;
        setIsImporting(true);
        try {
            if (!window.pywebview || !window.pywebview.api) return;
            const result = await window.pywebview.api.import_config();
            if (result && result.success) {
                window.location.reload();
            } else if (result && result.error && result.error !== "No file selected") {
                alert("Import failed: " + result.error);
            }
        } catch (e) {
            alert("Import failed: " + e);
        } finally {
            setIsImporting(false);
        }
    };

    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const q = e.target.value;
        setSearchQuery(q);
        if (!q.trim()) {
            setSearchResults([]);
            return;
        }

        const lowerQ = q.toLowerCase();
        const results = SEARCH_INDEX.map(item => {
            const indexStr = (item.title + " " + item.tab + " " + item.keywords.join(" ")).toLowerCase();
            return { item, match: indexStr.includes(lowerQ) };
        }).filter(x => x.match).map(x => x.item);

        setSearchResults(results);
    };

    const handleSearchSelect = (result: typeof SEARCH_INDEX[0]) => {
        if (setActiveTab) {
            setActiveTab(result.tab);
            setTimeout(() => {
                if ((window as any).find && searchQuery.trim().length >= 3) {
                    (window as any).find(searchQuery, false, false, true, false, false, false);
                }
            }, 300);
        }
        setSearchQuery("");
        setSearchResults([]);
        setIsSearchFocused(false);
    };

    const handleThemeWheel = useCallback((e: React.WheelEvent) => {
        e.preventDefault();
        const idx = themes.findIndex((t) => t.id === theme);
        if (idx === -1) return;
        const next = e.deltaY > 0
            ? (idx + 1) % themes.length
            : (idx - 1 + themes.length) % themes.length;
        onThemeChange(themes[next].id);
    }, [theme, onThemeChange]);

    return (
        <div className={`header-bar ${isGlitching ? "glitch-no-drag" : ""}`}>
            <div className="header-left">
                <button
                    className={`btn ${isRunning ? "btn-stop" : "btn-start"}`}
                    onClick={onToggle}
                    tabIndex={-1}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            e.stopPropagation();
                        }
                    }}
                    style={{
                        padding: "4px 12px",
                        fontSize: "12px",
                        whiteSpace: "nowrap",
                        flexShrink: 0
                    }}
                >
                    {isRunning ? "■ Stop (F2)" : "▶ Start (F1)"}
                </button>

                <div className={`status-badge ${isRunning ? "running" : "idle"}`}>
                    <span className="status-dot" />
                    {isRunning ? "Running" : "Idle"}
                </div>

                <button
                    className={`pin-btn ${alwaysOnTop ? "active" : ""}`}
                    onClick={toggleAlwaysOnTop}
                    title={alwaysOnTop ? "Unpin from top" : "Always on top"}
                >
                    📌
                </button>
            </div>

            <div className="header-right">
                <div style={{ position: "relative", marginRight: "10px" }}>
                    <div style={{ position: "absolute", left: "8px", top: "50%", transform: "translateY(-50%)", fontSize: "12px", color: "var(--text-muted)", pointerEvents: "none" }}>
                        🔍
                    </div>
                    <input
                        type="text"
                        className="form-input"
                        placeholder="Filter index"
                        value={searchQuery}
                        onChange={handleSearchChange}
                        onFocus={() => setIsSearchFocused(true)}
                        onBlur={() => setTimeout(() => setIsSearchFocused(false), 200)}
                        style={{
                            width: "110px",
                            fontSize: "12px",
                            padding: "4px 8px 4px 26px"
                        }}
                    />
                    {isSearchFocused && searchResults.length > 0 && (
                        <div style={{
                            position: "absolute",
                            top: "100%",
                            right: 0,
                            marginTop: "8px",
                            background: "var(--bg-card)",
                            border: "1px solid var(--border)",
                            borderRadius: "var(--radius-md)",
                            boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
                            zIndex: 1000,
                            minWidth: "200px",
                            maxHeight: "300px",
                            overflowY: "auto"
                        }}>
                            {searchResults.map((res, i) => (
                                <div
                                    key={i}
                                    onClick={() => handleSearchSelect(res)}
                                    style={{
                                        padding: "8px 12px",
                                        cursor: "pointer",
                                        borderBottom: i < searchResults.length - 1 ? "1px solid rgba(255,255,255,0.1)" : "none",
                                        fontSize: "12px",
                                        transition: "background 0.2s ease"
                                    }}
                                    onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
                                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                                >
                                    <div style={{ color: "var(--text-primary)", fontWeight: 500, marginBottom: "2px" }}>{res.title}</div>
                                    <div style={{ color: "var(--text-muted)", fontSize: "11px" }}>Switch to {res.tab} tab ➜</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <button
                    className="btn btn-import"
                    onClick={handleImportConfig}
                    disabled={isImporting}
                    title="Import a config.json file"
                    style={{
                        fontSize: "11px",
                        padding: "4px 8px",
                        marginRight: "10px",
                        cursor: isImporting ? "wait" : "pointer",
                        whiteSpace: "nowrap",
                        flexShrink: 0
                    }}
                >
                    {isImporting ? "Importing..." : "Import Config"}
                </button>

                <span style={{ fontSize: "12px", color: "var(--text-secondary)", marginRight: "6px" }}>
                    Macro Theme:
                </span>
                <select
                    className="form-input"
                    value={theme}
                    onChange={(e) => onThemeChange(e.target.value)}
                    onWheel={handleThemeWheel}
                    style={{
                        width: "130px",
                        fontSize: "12px",
                        padding: "4px 8px",
                        cursor: "pointer",
                    }}
                >
                    {themes.map((t) => (
                        <option key={t.id} value={t.id}>{t.label}</option>
                    ))}
                </select>
            </div>
        </div>
    );
}
