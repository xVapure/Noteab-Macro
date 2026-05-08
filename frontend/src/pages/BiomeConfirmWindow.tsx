import { useState, useEffect } from "react";
import "../App.css";

export default function BiomeConfirmWindow() {
    const params = new URLSearchParams(window.location.search);
    const biome = (window as any).__INJECTED_BIOME__ || params.get("biome") || "UNKNOWN";

    const [countdown, setCountdown] = useState(10);
    const [responded, setResponded] = useState(false);

    useEffect(() => {
        if (responded) return;
        if (countdown <= 0) return;
        const interval = setInterval(() => {
            setCountdown(prev => prev - 1);
        }, 1000);
        return () => clearInterval(interval);
    }, [countdown, responded]);

    const handleConfirm = async () => {
        if (responded) return;
        setResponded(true);
        try {
            if (window.pywebview?.api?.confirm_biome_response) {
                await window.pywebview.api.confirm_biome_response(true);
            }
        } catch (e) {
            console.error("confirm_biome_response error:", e);
        }
    };

    const handleCancel = async () => {
        if (responded) return;
        setResponded(true);
        try {
            if (window.pywebview?.api?.confirm_biome_response) {
                await window.pywebview.api.confirm_biome_response(false);
            }
        } catch (e) {
            console.error("confirm_biome_response error:", e);
        }
    };

    return (
        <div style={{
            height: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--bg-dark)",
            color: "var(--text-primary)",
            padding: "24px",
            position: "relative",
            textAlign: "center",
            overflow: "hidden",
        }}>
            <div className="corner-bracket tl" style={{ top: 5, left: 5 }} />
            <div className="corner-bracket tr" style={{ top: 5, right: 5 }} />
            <div className="corner-bracket bl" style={{ bottom: 5, left: 5 }} />
            <div className="corner-bracket br" style={{ bottom: 5, right: 5 }} />

            <div style={{ fontSize: "42px", marginBottom: "10px" }}>⚠️</div>

            <h2 style={{
                fontSize: "18px",
                fontWeight: 700,
                color: "#ff6b6b",
                marginBottom: "8px",
            }}>
                Rare Biome Detected After Rejoin!
            </h2>

            <div style={{
                fontSize: "28px",
                fontWeight: 800,
                color: "var(--accent)",
                marginBottom: "14px",
            }}>
                {biome}
            </div>

            <p style={{
                fontSize: "13px",
                lineHeight: 1.5,
                color: "var(--text-secondary)",
                marginBottom: "20px",
            }}>
                You just rejoined a server that has a <b style={{ color: "#ff6b6b" }}>rare biome</b> active.<br />
                Did you forget to close the macro before joining?<br /><br />
                If you forgot, the macro will <b style={{ color: "#ff6b6b" }}>stop immediately!!</b>
            </p>

            {!responded ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", width: "100%" }}>
                    <button
                        onClick={handleConfirm}
                        style={{
                            padding: "12px 20px",
                            border: "none",
                            borderRadius: "8px",
                            fontSize: "13px",
                            fontWeight: 600,
                            cursor: "pointer",
                            background: "linear-gradient(135deg, #00b894, #00cec9)",
                            color: "#fff",
                        }}
                    >
                        ✅ Nah. I'm good, keep this tuff macro running 🗣️🔥
                    </button>
                    <button
                        onClick={handleCancel}
                        style={{
                            padding: "12px 20px",
                            border: "none",
                            borderRadius: "8px",
                            fontSize: "13px",
                            fontWeight: 600,
                            cursor: "pointer",
                            background: "linear-gradient(135deg, #e74c3c, #fd79a8)",
                            color: "#fff",
                        }}
                    >
                        ❌ I forgot to turn the macro off please spare me 😭🥀
                    </button>
                </div>
            ) : (
                <div style={{ fontSize: "14px", color: "var(--accent)" }}>
                    Response sent!
                </div>
            )}

            <div style={{
                marginTop: "14px",
                fontSize: "12px",
                color: "var(--text-secondary)",
                opacity: 0.6,
            }}>
                {responded ? "" : countdown > 0 ? `Auto-continuing in ${countdown}s...` : "Auto-continuing..."}
            </div>
        </div>
    );
}
