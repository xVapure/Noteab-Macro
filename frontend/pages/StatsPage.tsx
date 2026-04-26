import { useState, useEffect, useRef, useCallback } from "react";
import { useConfig } from "../contexts/ConfigContext";

const GLITCH_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()[]{}<>?/\\|~`";

function GlitchText() {
    const [text, setText] = useState("GLITCHED");
    const frameRef = useRef(0);
    const lastUpdateRef = useRef(0);

    const generateGlitchString = useCallback(() => {
        const len = 6 + Math.floor(Math.random() * 12);
        const chars: string[] = [];
        for (let i = 0; i < len; i++) {
            if (i > 0 && i % 4 === 0 && Math.random() > 0.5) {
                chars.push("-");
            } else {
                chars.push(GLITCH_CHARS[Math.floor(Math.random() * GLITCH_CHARS.length)]);
            }
        }
        return `[${chars.join("")}]`;
    }, []);

    useEffect(() => {
        const animate = (timestamp: number) => {
            if (timestamp - lastUpdateRef.current > 35) {
                setText(generateGlitchString());
                lastUpdateRef.current = timestamp;
            }
            frameRef.current = requestAnimationFrame(animate);
        };
        frameRef.current = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(frameRef.current);
    }, [generateGlitchString]);

    return (
        <span className="glitch-text">{text}</span>
    );
}

export default function StatsPage() {
    const { config, error, sessionDuration, lastStartTime, isMacroRunning } = useConfig();
    const [elapsedDisplay, setElapsedDisplay] = useState("00:00:00");

    useEffect(() => {
        const updateTimer = () => {
            let totalMs = sessionDuration;
            if (isMacroRunning && lastStartTime) {
                totalMs += (Date.now() - lastStartTime);
            }

            const hours = Math.floor(totalMs / (1000 * 60 * 60));
            const minutes = Math.floor((totalMs % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((totalMs % (1000 * 60)) / 1000);

            const pad = (n: number) => n.toString().padStart(2, "0");
            setElapsedDisplay(`${pad(hours)}:${pad(minutes)}:${pad(seconds)}`);
        };

        // Update immediately
        updateTimer();

        // Start interval
        const interval = setInterval(updateTimer, 1000);

        return () => clearInterval(interval);
    }, [sessionDuration, lastStartTime, isMacroRunning]);

    const biomeColors: Record<string, string> = {
        "WINDY": "#9ae5ff",
        "RAINY": "#027cbd",
        "SNOWY": "#Dceff9",
        "SAND STORM": "#8F7057",
        "HELL": "#ff4719",
        "STARFALL": "#011ab7",
        "CORRUPTION": "#6d32a8",
        "NULL": "#838383",
        "GLITCHED": "#bfff00",
        "DREAMSPACE": "#ea9dda",
        "CYBERSPACE": "#0A1A3D",
        "AURORA": "#56d6a0",
        "HEAVEN": "#dfaf63",
    };

    if (error) return (
        <div style={{ padding: "20px", color: "#ef4444" }}>
            <h3>Error Loading Stats</h3>
            <p>{error}</p>
        </div>
    );

    if (!config) return <div style={{ padding: "20px" }}>Loading stats...</div>;

    const biomeCounts = config.biome_counts || {};
    const totalBiomes = Object.entries(biomeCounts)
        .filter(([key]) => key !== "NORMAL")
        .reduce((a, [, count]) => a + Number(count), 0);

    const merchantCounts = config.merchant_counts || {};
    const totalMerchants = Object.values(merchantCounts).reduce((a, b) => a + Number(b), 0);

    const displayOrder = [
        "WINDY", "RAINY", "SNOWY", "SAND STORM",
        "HELL", "STARFALL", "CORRUPTION", "NULL",
        "GLITCHED", "DREAMSPACE", "CYBERSPACE",
        "AURORA", "HEAVEN"
    ];

    return (
        <>
            <div className="page-header">
                <h2>Stats</h2>
                <p>Session statistics and biome encounter history</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">⏱️</div>
                    <div>
                        <h3>Session Overview</h3>
                        <p>Current macro session statistics</p>
                    </div>
                </div>

                <div className="stats-grid">
                    <div className="stat-card accent">
                        <div className="stat-value">{elapsedDisplay}</div>
                        <div className="stat-label">Session Time</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{totalBiomes.toLocaleString()}</div>
                        <div className="stat-label">Total Biomes Founds</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{totalMerchants.toLocaleString()}</div>
                        <div className="stat-label">Merchants Found</div>
                    </div>
                </div>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🌍</div>
                    <div>
                        <h3>Biome Count Section</h3>
                    </div>
                </div>

                <div className="stats-grid">
                    {displayOrder.map((name) => (
                        <div key={name} className="stat-card">
                            <div className="stat-value">{biomeCounts[name] || 0}</div>
                            <div className="stat-label" style={{ color: biomeColors[name] }}>
                                {name === "GLITCHED" ? <GlitchText /> : name}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </>
    );
}
