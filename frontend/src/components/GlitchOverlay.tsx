import { useState, useEffect } from "react";
import "./GlitchOverlay.css";

const GIBBERISH_WORDS = [
    "CONNECTION_LOST", "ERR_NAME_NOT_RESOLVED", "FATAL_SYSTEM_EXCEPTION",
    "PAGE_FAULT_IN_NONPAGED_AREA", "IRQL_NOT_LESS_OR_EQUAL", "CRITICAL_PROCESS_DIED",
    "BAD_POOL_CALLER", "MEMORY_MANAGEMENT_FAULT", "0x000000A5",
    "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED", "[WARN] HEAP_CORRUPTION",
    "KERNEL_DATA_INPAGE_ERROR", "DATA_BUS_ERROR", "REGISTRY_ERROR",
    "WSAECONNRESET_10054", "0xFFFFFFFF", "INACCESSIBLE_BOOT_DEVICE",
    "SECURE_PCI_CONFIG_SPACE_ACCESS_VIOLATION", "GLITCHED_BIOME????????@@3^^@"
];

export default function GlitchOverlay() {
    const bars = Array.from({ length: 35 }).map((_, i) => ({
        id: i,
        top: Math.random() * 100,
        height: Math.random() * 2 + 0.2, // Thin tear lines
        delay: Math.random() * 0.2,      // Fast pop-in
        duration: Math.random() * 0.1 + 0.05 // Aggressive flicker speed
    }));

    const [glitchText, setGlitchText] = useState<{ id: number, text: string, delay: number, dur: number, top: number, left: number, scale: number }[]>([]);
    const [glitchBlocks, setGlitchBlocks] = useState<{ id: number, top: number, left: number, width: number, height: number, color: string, delay: number }[]>([]);

    useEffect(() => {
        const generateGlitchElements = () => {
            // Generate Random Text
            setGlitchText(Array.from({ length: 14 }).map((_) => ({
                id: Math.random(),
                text: GIBBERISH_WORDS[Math.floor(Math.random() * GIBBERISH_WORDS.length)],
                delay: Math.random() * 1,
                dur: Math.random() * 0.5 + 0.2,
                top: Math.random() * 90 + 5,
                left: Math.random() * 80 + 5,
                scale: Math.random() * 0.6 + 0.7 // Random size multiplier between 0.7x and 1.3x
            })));

            // Generate Random Corrupted Color Blocks
            const colors = ['red', 'green', 'blue'];
            setGlitchBlocks(Array.from({ length: 20 }).map((_) => ({
                id: Math.random(),
                top: Math.random() * 100,
                left: Math.random() * 100,
                width: Math.random() * 150 + 20,
                height: Math.random() * 50 + 10,
                color: colors[Math.floor(Math.random() * colors.length)],
                delay: Math.random() * 0.5
            })));
        };

        generateGlitchElements();
        const interval = setInterval(generateGlitchElements, 600);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="glitch-container">
            <div className="glitch-vignette" />
            <div className="glitch-scanlines" />
            <div className="glitch-rgb-split" />
            <div className="glitch-noise" />
            {bars.map(bar => (
                <div
                    key={bar.id}
                    className="glitch-bar"
                    style={{
                        top: `${bar.top}%`,
                        height: `${bar.height}%`,
                        animationDelay: `${bar.delay}s`,
                        animationDuration: `${bar.duration}s`
                    }}
                />
            ))}
            {glitchBlocks.map(block => (
                <div
                    key={block.id}
                    className={`glitch-block ${block.color}`}
                    style={{
                        top: `${block.top}%`,
                        left: `${block.left}%`,
                        width: `${block.width}px`,
                        height: `${block.height}px`,
                        animationDelay: `${block.delay}s`
                    }}
                />
            ))}
            <div className="glitch-gibberish">
                {glitchText.map(gt => (
                    <div
                        key={gt.id}
                        className="glitch-text-element"
                        style={{
                            animationDelay: `${gt.delay}s`,
                            animationDuration: `${gt.dur}s`,
                            top: `${gt.top}%`,
                            left: `${gt.left}%`,
                            fontSize: `${gt.scale}rem`
                        }}
                    >
                        {gt.text}
                    </div>
                ))}
            </div>
        </div>
    );
}

