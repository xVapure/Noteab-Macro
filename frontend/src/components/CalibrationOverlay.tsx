import { useEffect, useRef, useState } from "react";
// Remove tauri

interface CalibrationOverlayProps {
    mode: "point" | "region";
}

const CalibrationOverlay: React.FC<CalibrationOverlayProps> = ({ mode }) => {
    const [startPos, setStartPos] = useState<{ x: number; y: number; px: number; py: number } | null>(null);
    const [currentPos, setCurrentPos] = useState<{ x: number; y: number } | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
    const [imgSize, setImgSize] = useState<{ w: number; h: number }>({ w: 1920, h: 1080 });
    const [loading, setLoading] = useState(true);
    const containerRef = useRef<HTMLDivElement>(null);
    // Remove appWindow
    const toPhysical = (clientX: number, clientY: number) => {
        const el = containerRef.current;
        if (!el) return { px: clientX, py: clientY };
        const rect = el.getBoundingClientRect();
        const rx = (clientX - rect.left) / rect.width;
        const ry = (clientY - rect.top) / rect.height;
        return {
            px: Math.round(rx * imgSize.w),
            py: Math.round(ry * imgSize.h)
        };
    };

    useEffect(() => {
        const originalHtmlBg = document.documentElement.style.background;
        const originalBodyBg = document.body.style.background;
        document.documentElement.style.background = "transparent";
        document.body.style.background = "transparent";

        if (mode === "region") {
            if (window.pywebview && window.pywebview.api) {
                window.pywebview.api.take_calibration_screenshot().then((res: any) => {
                    const [filePath, w, h] = res;
                    setImgSize({ w, h });
                    const url = `file://${filePath}`;
                    setScreenshotUrl(url);
                    setLoading(false);
                    console.log(`[Calibration] Screenshot loaded: ${w}x${h} from ${filePath}`);
                }).catch((err: any) => {
                    console.error("Failed to take calibration screenshot", err);
                    setLoading(false);
                });
            } else {
                setLoading(false);
            }
        } else {
            setLoading(false);
        }

        const handleKeyDown = async (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                if (window.pywebview) window.pywebview.api.close_window();
            }
        };
        window.addEventListener("keydown", handleKeyDown);

        return () => {
            document.documentElement.style.background = originalHtmlBg;
            document.body.style.background = originalBodyBg;
            window.removeEventListener("keydown", handleKeyDown);
        };
    }, [mode]);

    const handleMouseDown = (e: React.MouseEvent) => {
        if ((e.target as HTMLElement).tagName === "BUTTON") return;

        if (mode === "point") {
            const dpr = window.devicePixelRatio || 1;
            finishCalibration({
                x: Math.round(e.screenX * dpr),
                y: Math.round(e.screenY * dpr)
            });
        } else {
            const { px, py } = toPhysical(e.clientX, e.clientY);
            setStartPos({ x: e.clientX, y: e.clientY, px, py });
            setCurrentPos({ x: e.clientX, y: e.clientY });
            setIsDragging(true);
        }
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (isDragging) {
            setCurrentPos({ x: e.clientX, y: e.clientY });
        }
    };

    const handleMouseUp = (e: React.MouseEvent) => {
        if (mode === "region" && isDragging && startPos) {
            setIsDragging(false);
            const { px: endPx, py: endPy } = toPhysical(e.clientX, e.clientY);
            const x = Math.min(startPos.px, endPx);
            const y = Math.min(startPos.py, endPy);
            const w = Math.abs(endPx - startPos.px);
            const h = Math.abs(endPy - startPos.py);
            finishCalibration({ x, y, w, h });
        }
    };

    const finishCalibration = async (data: any) => {
        console.log("[Calibration] Result:", data);
        try {
            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.emit_calibration_result(data);
                await window.pywebview.api.close_window();
            }
        } catch (err) {
            console.error("Failed to emit/close", err);
            if (window.pywebview) window.pywebview.api.close_window();
        }
    };

    return (
        <div
            ref={containerRef}
            style={{
                width: "100vw",
                height: "100vh",
                cursor: "crosshair",
                position: "relative",
                userSelect: "none",
                overflow: "hidden",
                background: screenshotUrl ? "none" : "rgba(0, 0, 0, 0.5)"
            }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
        >
            {/* Screenshot background - stretched to fill window */}
            {screenshotUrl && (
                <img
                    src={screenshotUrl}
                    alt=""
                    style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: "100%",
                        objectFit: "fill",
                        pointerEvents: "none",
                        zIndex: 0
                    }}
                />
            )}
            {/* Slight dark overlay for contrast */}
            <div style={{
                position: "absolute",
                top: 0, left: 0, width: "100%", height: "100%",
                background: "rgba(0, 0, 0, 0.15)",
                pointerEvents: "none",
                zIndex: 1
            }} />
            {/* Cancel button */}
            <button
                onClick={() => { if (window.pywebview) window.pywebview.api.close_window() }}
                style={{
                    position: "absolute",
                    top: "20px",
                    right: "20px",
                    background: "#ef4444",
                    color: "white",
                    border: "none",
                    padding: "8px 16px",
                    borderRadius: "4px",
                    cursor: "pointer",
                    zIndex: 1000,
                    fontWeight: "bold",
                    pointerEvents: "auto"
                }}
            >
                Cancel (ESC)
            </button>
            {/* Selection rectangle */}
            {mode === "region" && isDragging && startPos && currentPos && (
                <div
                    style={{
                        position: "absolute",
                        left: Math.min(startPos.x, currentPos.x),
                        top: Math.min(startPos.y, currentPos.y),
                        width: Math.abs(currentPos.x - startPos.x),
                        height: Math.abs(currentPos.y - startPos.y),
                        border: "2px solid #00ff00",
                        background: "rgba(0, 255, 0, 0.15)",
                        pointerEvents: "none",
                        zIndex: 500
                    }}
                />
            )}
            {/* Instructions */}
            {!isDragging && (
                <div style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    pointerEvents: "none",
                    textAlign: "center",
                    color: "white",
                    textShadow: "0 2px 4px black, 0 0 10px black",
                    zIndex: 10
                }}>
                    {loading ? (
                        <p style={{ fontWeight: "bold", fontSize: "20px" }}>Taking screenshot... (This shouldn't take long)</p>
                    ) : (
                        <>
                            <p style={{ fontWeight: "bold", fontSize: "20px" }}>
                                {mode === "point" ? "Click to Select Position" : "Drag to Select Region"}
                            </p>
                            <p style={{ fontSize: "14px" }}>Press ESC to cancel</p>
                            <p style={{ fontSize: "12px", opacity: 0.7 }}>
                                Screenshot: {imgSize.w}×{imgSize.h}px
                            </p>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default CalibrationOverlay;
