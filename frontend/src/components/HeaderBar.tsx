import { useState, useCallback } from "react";
interface HeaderBarProps {
    isRunning: boolean;
    onToggle: () => void;
    theme: string;
    onThemeChange: (theme: string) => void;
    isGlitching: boolean;
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

export default function HeaderBar({ isRunning, onToggle, theme, onThemeChange, isGlitching }: HeaderBarProps) {
    const [alwaysOnTop, setAlwaysOnTop] = useState(false);
    const [isImporting, setIsImporting] = useState(false);

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
                <button
                    className="btn btn-import"
                    onClick={handleImportConfig}
                    disabled={isImporting}
                    title="Import a config.json file"
                    style={{
                        fontSize: "11px",
                        padding: "4px 10px",
                        marginRight: "10px",
                        cursor: isImporting ? "wait" : "pointer",
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
