import { useConfig } from "../contexts/ConfigContext";
import { useState, useEffect, useRef } from "react";

export default function CustomizationPage() {
    const { config, saveConfig } = useConfig();
    const handleSave = (newConfig: any) => {
        saveConfig(newConfig as any);
    };

    const [biomes, setBiomes] = useState<Record<string, { color: string; thumbnail_url: string; start_description?: string; end_description?: string }>>({});
    const [selectedBiome, setSelectedBiome] = useState<string>("");
    const selectRef = useRef<HTMLSelectElement>(null);

    useEffect(() => {
        if (config && config.custom_biome_overrides) {
            const parsed = JSON.parse(JSON.stringify(config.custom_biome_overrides));
            setBiomes(parsed);
            
            if (!selectedBiome) {
                const keys = Object.keys(parsed).filter(b => b !== "NORMAL" && b !== "DREAMSPACE");
                if (keys.length > 0) setSelectedBiome(keys[0]);
            }
        }
    }, [config]);

    const handleBiomeChange = (field: "color" | "thumbnail_url", value: string) => {
        if (!selectedBiome) return;
        setBiomes(prev => ({
            ...prev,
            [selectedBiome]: {
                ...prev[selectedBiome],
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
    };

    if (!config) return <div>Loading...</div>;

    const biomeKeys = Object.keys(biomes).filter(b => b !== "NORMAL" && b !== "DREAMSPACE");
    
    useEffect(() => {
        const el = selectRef.current;
        if (!el) return;

        const handleNativeWheel = (e: WheelEvent) => {
            e.preventDefault();
            if (!biomeKeys.length) return;
            
            setSelectedBiome(prev => {
                const currentIndex = biomeKeys.indexOf(prev);
                if (currentIndex === -1) return prev;
                
                let newIndex = currentIndex;
                if (e.deltaY < 0) {
                    newIndex = (currentIndex - 1 + biomeKeys.length) % biomeKeys.length;
                } else if (e.deltaY > 0) {
                    newIndex = (currentIndex + 1) % biomeKeys.length;
                }
                return biomeKeys[newIndex];
            });
        };

        el.addEventListener("wheel", handleNativeWheel, { passive: false });
        return () => el.removeEventListener("wheel", handleNativeWheel);
    }, [biomeKeys]);
    
    // Fallbacks just in case
    const currentBiomeData = biomes[selectedBiome] || { color: "#ffffff", thumbnail_url: "" };
    const rawColor = currentBiomeData.color || "#ffffff";
    const cssColor = rawColor.startsWith("0x") ? "#" + rawColor.slice(2) : rawColor;
    
    // current timestamp
    const now = new Date();
    const timeOptions: Intl.DateTimeFormatOptions = { 
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', 
        hour: 'numeric', minute: 'numeric', hour12: true 
    };
    const formattedDate = now.toLocaleDateString('en-US', timeOptions);

    return (
        <div className="page-container fade-in" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
            <div className="page-header">
                <h2>Discord Webhook Customization</h2>
                <p>Dynamically configure what your webhook embeds look like when a biome starts</p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "10px", minHeight: "0", maxWidth: "560px", margin: "0 auto", paddingBottom: "30px" }}>

                {/* TOP: Discord Simulator */}
                <div 
                    style={{ 
                        backgroundColor: "#313338", 
                        borderRadius: "8px", 
                        border: "1px solid rgba(255,255,255,0.05)",
                        padding: "16px",
                        height: "fit-content",
                        overflowY: "auto",
                        display: "flex",
                        fontFamily: "'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif"
                    }}
                >
                    {/* Simulated Discord Message */}
                    <div style={{ display: "flex", gap: "12px", width: "100%" }}>
                        {/* Avatar */}
                        <div style={{ 
                            width: "40px", height: "40px", borderRadius: "50%", 
                            backgroundColor: "#5865F2", flexShrink: 0,
                            backgroundImage: "url('https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png')",
                            backgroundSize: "cover"
                        }}></div>
                        
                        {/* Message Content */}
                        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
                            <div style={{ display: "flex", alignItems: "baseline", gap: "6px", marginBottom: "2px", flexWrap: "wrap" }}>
                                <span style={{ color: "#F2F3F5", fontSize: "15px", fontWeight: "500", lineHeight: "1.2" }}>Your webhook name go here cuz idk</span>
                                <span style={{ 
                                    backgroundColor: "#5865F2", color: "#FFFFFF", fontSize: "9px", 
                                    padding: "0 4px", borderRadius: "3px", fontWeight: "600",
                                    lineHeight: "13px", height: "13px", verticalAlign: "middle"
                                }}>APP</span>
                                <span style={{ color: "#949BA4", fontSize: "11px", marginLeft: "2px" }}>Today at {now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                            </div>

                            {/* Embed Container */}
                            <div style={{ 
                                backgroundColor: "#2b2d31", 
                                borderLeft: `4px solid ${cssColor || '#FFFFFF'}`,
                                borderRadius: "4px",
                                display: "flex",
                                padding: "12px 14px",
                                marginTop: "4px"
                            }}>
                                <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: 0 }}>
                                    
                                    {/* Embed Title (Timestamp markdown emulation) */}
                                    <div style={{ 
                                        color: "#F2F3F5", 
                                        fontSize: "14px", 
                                        fontWeight: "600",
                                        wordBreak: "break-word",
                                        marginBottom: "2px"
                                    }}>
                                        <span style={{ 
                                            backgroundColor: "rgba(255,255,255,0.06)", 
                                            padding: "2px 4px", 
                                            borderRadius: "3px" 
                                        }}>
                                            {formattedDate} (just now)
                                        </span>
                                    </div>

                                    {/* Embed Description (Markdown Emulation) */}
                                    <div style={{ 
                                        fontSize: "13px", 
                                        color: "#DBDEE1", 
                                        lineHeight: "1.2",
                                        whiteSpace: "pre-wrap"
                                    }}>
                                        {/* Blockquote wrapper */}
                                        <div style={{
                                            borderLeft: "4px solid #4e5058",
                                            padding: "0 10px",
                                            marginLeft: "0"
                                        }}>
                                            <div style={{ 
                                                fontSize: "18px", 
                                                fontWeight: "700", 
                                                color: "#F2F3F5",
                                                marginTop: "16px",
                                                marginBottom: "12px",
                                                lineHeight: "1.4",
                                                display: "flex", gap: "6px",
                                                wordBreak: "break-word"
                                            }}>
                                                {`Biome Started - ${selectedBiome || "SNOWY"}`}
                                            </div>
                                            
                                            <div style={{ 
                                                fontSize: "16px", 
                                                fontWeight: "600",
                                                marginTop: "12px",
                                                marginBottom: "6px"
                                            }}>
                                                <a href="#" style={{ color: "#00A8FC", textDecoration: "none" }} onClick={e => e.preventDefault()}>Join Server</a>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Footer */}
                                    <div style={{ 
                                        display: "flex", 
                                        alignItems: "center", 
                                        gap: "6px", 
                                        marginTop: "4px" 
                                    }}>
                                        <img src="https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png" style={{ width: "16px", height: "16px", borderRadius: "50%" }} alt="footer" />
                                        <span style={{ color: "#949BA4", fontSize: "11px", fontWeight: "500" }}>Coteab Macro v2.1.6-beta1 • Today at {now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                                    </div>
                                </div>
                                
                                {/* Thumbnail */}
                                {currentBiomeData.thumbnail_url && (
                                    <div style={{ marginLeft: "12px", flexShrink: 0 }}>
                                        <img 
                                            src={currentBiomeData.thumbnail_url} 
                                            style={{ maxWidth: "60px", maxHeight: "60px", borderRadius: "4px", objectFit: "contain" }} 
                                            alt="thumbnail"
                                            onError={(e) => {
                                                (e.target as HTMLImageElement).style.display = 'none';
                                            }}
                                            onLoad={(e) => {
                                                (e.target as HTMLImageElement).style.display = 'block';
                                            }}
                                        />
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
                
                {/* MIDDLE: Select Biome */}
                <div className="card" title="Scroll with your mouse wheel here to quickly cycle through biomes!">
                    <label className="form-label" style={{ display: "flex", justifyContent: "space-between" }}>
                        Select Biome
                        <span style={{ fontSize: "0.8em", color: "#64748b", fontWeight: "normal" }}>(Scroll wheel supported)</span>
                    </label>
                    <select 
                        ref={selectRef}
                        className="form-input" 
                        style={{ width: "100%", padding: "10px", fontSize: "1.1em", cursor: "pointer", appearance: "auto" }}
                        value={selectedBiome}
                        onChange={(e) => setSelectedBiome(e.target.value)}
                    >
                        {biomeKeys.map(b => (
                            <option key={b} value={b}>{b}</option>
                        ))}
                    </select>
                </div>

                {/* BOTTOM: Config Inputs */}
                <div className="card" style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                        <div>
                            <label className="form-label" style={{ display: "flex", justifyContent: "space-between" }}>
                                Hex Color
                                <a href="#" style={{ color: "#0ea5e9", fontSize: "0.8em", textDecoration: "none" }} onClick={(e) => { e.preventDefault(); if ((window as any).pywebview) (window as any).pywebview.api.open_url("https://htmlcolorcodes.com/"); }}>
                                    Get Colors
                                </a>
                            </label>
                            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                                <input 
                                    type="color" 
                                    style={{ width: "40px", height: "40px", padding: "0", border: "none", borderRadius: "8px", cursor: "pointer", background: "none" }}
                                    value={cssColor}
                                    onChange={(e) => handleBiomeChange("color", e.target.value)}
                                />
                                <input 
                                    type="text" 
                                    className="form-input" 
                                    style={{ flex: 1, fontFamily: "monospace" }}
                                    value={currentBiomeData.color}
                                    onChange={(e) => handleBiomeChange("color", e.target.value)}
                                    placeholder="#FFFFFF"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="form-label">Thumbnail URL</label>
                            <input 
                                type="text" 
                                className="form-input" 
                                style={{ width: "100%", fontSize: "0.95em" }}
                                value={currentBiomeData.thumbnail_url}
                                onChange={(e) => handleBiomeChange("thumbnail_url", e.target.value)}
                                placeholder="https://..."
                            />
                        </div>


                        
                        <button className="btn btn-primary" style={{ backgroundColor: "#d97706", marginTop: "10px" }} onClick={saveBiomes}>
                            Save Configuration (reopen the macro to take effect!)
                        </button>
                    </div>
                </div>
            </div>
    );
}
