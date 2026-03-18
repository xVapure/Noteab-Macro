
import { useConfig } from "../contexts/ConfigContext";
import { useState, useEffect } from "react";
// Remove tauri

export default function CustomizationPage() {
    const { config, saveConfig } = useConfig();
    const handleSave = (newConfig: any) => {
        saveConfig(newConfig as any);
    };

    const [showBiomeModal, setShowBiomeModal] = useState(false);
    const [biomes, setBiomes] = useState<Record<string, { color: string; thumbnail_url: string }>>({});

    useEffect(() => {
        if (showBiomeModal && config) {
            if (config.custom_biome_overrides) {
                setBiomes(JSON.parse(JSON.stringify(config.custom_biome_overrides)));
            }
        }
    }, [showBiomeModal, config]);

    const handleBiomeChange = (biome: string, field: "color" | "thumbnail_url", value: string) => {
        setBiomes(prev => ({
            ...prev,
            [biome]: {
                ...prev[biome],
                [field]: value
            }
        }));
    };

    const saveBiomes = () => {
        if (!config) return;
        handleSave({
            ...config,
            custom_biome_overrides: biomes
        });
        setShowBiomeModal(false);
    };

    if (!config) return <div>Loading...</div>;

    const biomeKeys = Object.keys(biomes).filter(b => b !== "NORMAL");

    return (
        <div className="page-container fade-in">
            <div className="page-header">
                <h2>Customizations</h2>
                <p>Customize the biome webhook embeds to your liking (Pls add femboy Vapure embed for free robux)</p>
            </div>

            <div className="card">
                <div style={{ marginTop: "10px" }}>
                    <button className="btn btn-primary" style={{ backgroundColor: "#d97706", width: "100%" }} onClick={() => setShowBiomeModal(true)}>
                        Customize Biome Embed
                    </button>
                </div>
            </div>

            {/* Modal */}
            {showBiomeModal && (
                <div className="modal-overlay" onClick={() => setShowBiomeModal(false)}>
                    <div
                        className="modal-content"
                        onClick={e => e.stopPropagation()}
                        style={{
                            maxWidth: "800px",
                            width: "95%",
                            maxHeight: "85vh",
                            display: "flex",
                            flexDirection: "column",
                            background: "var(--bg-card)",
                            border: "1px solid var(--border)",
                            borderRadius: "var(--radius-lg)",
                            padding: "0"
                        }}
                    >
                        {/* Header */}
                        <div style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            padding: "15px 20px",
                            borderBottom: "1px solid var(--border)",
                            background: "rgba(0,0,0,0.1)"
                        }}>
                            <h3 style={{ margin: 0, fontSize: "1.2rem" }}>Customize Biome Embed</h3>
                            <button
                                className="btn"
                                onClick={() => setShowBiomeModal(false)}
                                style={{
                                    padding: "4px 10px",
                                    minWidth: "auto",
                                    background: "transparent",
                                    border: "1px solid var(--border)",
                                    color: "var(--text-secondary)"
                                }}
                            >
                                ✕
                            </button>
                        </div>

                        {/* body scroll */}
                        <div style={{
                            flex: 1,
                            overflowY: "auto",
                            padding: "20px"
                        }}>
                            <div className="biome-grid-header" style={{
                                display: "grid",
                                gridTemplateColumns: "120px 100px 1fr",
                                gap: "15px",
                                marginBottom: "10px",
                                fontWeight: "bold",
                                color: "var(--text-muted)",
                                fontSize: "0.9rem",
                                textTransform: "uppercase",
                                letterSpacing: "0.5px"
                            }}>
                                <div>Biome</div>
                                <div>Color</div>
                                <div>Thumbnail URL</div>
                            </div>

                            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                                {biomeKeys.map(biome => (
                                    <div key={biome} style={{
                                        display: "grid",
                                        gridTemplateColumns: "120px 100px 1fr",
                                        gap: "15px",
                                        alignItems: "center",
                                        background: "rgba(255,255,255,0.02)",
                                        padding: "8px",
                                        borderRadius: "6px"
                                    }}>
                                        <div style={{ fontWeight: "600", color: "var(--text-primary)" }}>{biome}</div>
                                        <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                                            <div style={{
                                                width: "16px",
                                                height: "16px",
                                                borderRadius: "4px",
                                                backgroundColor: biomes[biome]?.color || "#FFFFFF",
                                                border: "1px solid rgba(255,255,255,0.2)"
                                            }}></div>
                                            <input
                                                type="text"
                                                className="form-input"
                                                style={{ padding: "4px 8px", fontSize: "0.9em" }}
                                                value={biomes[biome]?.color || ""}
                                                onChange={e => handleBiomeChange(biome, "color", e.target.value)}
                                                placeholder="#"
                                            />
                                        </div>
                                        <input
                                            type="text"
                                            className="form-input"
                                            style={{ padding: "4px 8px", fontSize: "0.9em" }}
                                            value={biomes[biome]?.thumbnail_url || ""}
                                            onChange={e => handleBiomeChange(biome, "thumbnail_url", e.target.value)}
                                            placeholder="https://..."
                                        />
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* footer */}
                        <div style={{
                            padding: "15px 20px",
                            borderTop: "1px solid var(--border)",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            background: "rgba(0,0,0,0.1)"
                        }}>
                            <a href="#" style={{ color: "#0ea5e9", fontSize: "0.9em", textDecoration: "none", display: "flex", alignItems: "center", gap: "5px" }} onClick={(e) => { e.preventDefault(); if (window.pywebview) window.pywebview.api.open_url("https://htmlcolorcodes.com/"); }}>
                                <span>🎨 Get Color Codes Here!!</span>
                            </a>
                            <div style={{ display: "flex", gap: "10px" }}>
                                <button className="btn btn-primary" style={{ backgroundColor: "#d97706" }} onClick={saveBiomes}>
                                    Save Changes
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
