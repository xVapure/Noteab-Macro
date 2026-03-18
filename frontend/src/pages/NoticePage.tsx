import { useState, useEffect } from "react";
import React from "react";

export default function NoticePage() {
    const [content, setContent] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch("https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/noticetabcontents.txt")
            .then(res => res.text())
            .then(text => {
                setContent(text);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch notice:", err);
                setLoading(false);
            });
    }, []);

    const parseNotice = (text: string) => {
        const lines = text.split("\n");
        const elements: React.ReactNode[] = [];
        let currentList: React.ReactNode[] = [];
        let currentTitle: string | null = null;

        const flushSection = (key: number) => {
            if (currentTitle || currentList.length > 0) {
                elements.push(
                    <div key={key} className="changelog-item">
                        {currentTitle && <h4>{currentTitle}</h4>}
                        {currentList.length > 0 && <ul>{currentList}</ul>}
                    </div>
                );
                currentList = [];
                currentTitle = null;
            }
        };

        lines.forEach((line, i) => {
            const trimmed = line.trim();
            if (!trimmed) return;

            if (trimmed.startsWith("# ")) {
                flushSection(i);
                currentTitle = trimmed.substring(2);
            } else if (trimmed.startsWith("## ")) {
                // Treat ## as a sub-header or just bold text in the list for now, 
                // but the effective format seems to use it as a section divider too sometimes.
                // For this parser, let's treat it as a list header or just push a strong element.
                currentList.push(<li key={i} style={{ listStyle: "none", fontWeight: 700, marginLeft: "-1em", marginTop: "8px" }}>{trimmed.substring(3)}</li>);
            } else if (trimmed.startsWith("- ")) {
                currentList.push(<li key={i}>{trimmed.substring(2)}</li>);
            } else if (trimmed.startsWith("PLEASE WATCH")) {
                // Skip the top warning as we have our own banner, or render it specially?
                // The static UI has a tutorial banner, so we might check if we want to duplicate it.
                // For now, let's ignore it if it matches the specific header or just render as text.
            } else {
                // multiline text or other content
                currentList.push(<li key={i} style={{ listStyle: "none" }}>{trimmed}</li>);
            }
        });

        flushSection(lines.length);
        return elements;
    };

    return (
        <>
            <div className="page-header">
                <h2>Notice</h2>
                <p>Latest updates and patch notes</p>
            </div>

            <div className="info-banner">
                📺 New to Coteab? Watch the tutorial:{" "}
                <a href="https://www.youtube.com/watch?v=s2S7Bncx9ns" target="_blank" rel="noreferrer">
                    https://www.youtube.com/watch?v=s2S7Bncx9ns
                </a>
            </div>

            {loading ? (
                <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>
                    Loading notices...
                </div>
            ) : content ? (
                parseNotice(content)
            ) : (
                <div style={{ padding: "20px", textAlign: "center", color: "var(--text-danger)" }}>
                    Failed to load notices. Please check your connection.
                </div>
            )}

            <div className="info-banner" style={{ marginTop: "16px" }}>
                🌐 <a href="https://discord.gg/fw6q274Nrt" target="_blank" rel="noreferrer">JOIN OUR DEVELOPMENT SERVER</a> to keep in touch with the latest Coteab Macro updates!
            </div>
        </>
    );
}