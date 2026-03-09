export default function CreditsPage() {
    return (
        <>
            <div className="page-header">
                <h2>Credits</h2>
                <p>The people behind Coteab Macro</p>
            </div>

            {/* Developers Card */}
            <div className="card">
                <div style={{ display: "flex", justifyContent: "center", marginBottom: "16px" }}>
                    <img
                        src="https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/images/devteam3.png"
                        alt="Dev Team"
                        style={{
                            width: "120px",
                            height: "120px",
                            borderRadius: "8px",
                            border: "1px solid var(--border)",
                            boxShadow: "0 4px 6px rgba(0,0,0,0.1)"
                        }}
                    />
                </div>

                <div className="credits-list">
                    <div className="credit-item">
                        <div className="credit-avatar">V</div>
                        <div className="credit-info">
                            <ul style={{ margin: 0, paddingLeft: "16px", listStyle: "disc" }}>
                                <li><strong>Vapure/"@criticize."</strong> (Lead Developer, fullstack)</li>
                                <li><strong>Akito</strong> (Lead Developer, fullstack)</li>
                                <li><strong>Til/Comet</strong> (Developer, MacOS)</li>
                                <li><strong>ManasAarohi</strong> (Developer, path maker)</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px", marginTop: "16px" }}>
                    <a href="https://discord.gg/fw6q274Nrt" target="_blank" rel="noreferrer"
                        style={{ color: "var(--accent)", textDecoration: "underline" }}>
                        Join the Coteab Discord server!!!
                    </a>
                    <a href="https://github.com/xVapure/Noteab-Macro" target="_blank" rel="noreferrer" style={{ color: "var(--accent)", fontSize: "13px" }}>
                        GitHub: Coteab Macro!
                    </a>
                </div>
            </div>

            {/* Inspired By Card */}
            <div className="card" style={{ textAlign: "center" }}>
                <div style={{ display: "flex", justifyContent: "center", marginBottom: "12px" }}>
                    <img
                        src="https://avatars.githubusercontent.com/u/93678379?v=4"
                        alt="Maxstellar"
                        style={{
                            width: "120px",
                            height: "120px",
                            objectFit: "cover",
                            borderRadius: "8px",
                            border: "1px solid var(--border)"
                        }}
                    />
                </div>
                <h3>Inspired Biome Macro Creator: maxstellar</h3>
                <p>
                    <a href="https://www.youtube.com/@maxstellar_" target="_blank" rel="noreferrer"
                        style={{ color: "var(--accent)", textDecoration: "underline", cursor: "pointer" }}>
                        Their YT channel
                    </a>
                </p>
            </div>

            {/* Extra Credits */}
            <div className="card">
                <div className="card-header">
                    <div className="card-icon">🏅</div>
                    <div>
                        <h3>Extra Credits</h3>
                        <p>Thank you to everyone who helped along the way</p>
                    </div>
                </div>

                <div style={{
                    padding: "14px 16px",
                    background: "var(--bg-input)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-md)",
                    fontSize: "13px",
                    lineHeight: "1.8",
                    color: "var(--text-secondary)",
                }}>
                    <div>- maxstellar - Inspiration and I used some of his logic & former developer.</div>
                    <div>- Vexthecoder - Thank you for the icons &lt;3</div>
                    <div>- Cresqnt, Baz & the Scope Team - Anti-AFK inspiration.</div>
                    <div>- rnd.xy, imsomeone - For doing external works that I was too lazy to do tysm.</div>
                    <div>- Finnerinch - Former developer.</div>
                    <div>- .ivelchampion249._30053 - Fishing logic inspiration.</div>
                    <div>- All the testers that made the update possible with as less flaws as possible. Notably: "gummyballer", "mightbeanormalguest", "xdec27.", "gonebon", "kira_drago2",  and others.</div>
                </div>
            </div>

            <div className="info-banner" style={{ marginTop: "16px" }}>
                🌐 <a href="https://discord.gg/fw6q274Nrt" target="_blank" rel="noreferrer">JOIN OUR DEVELOPMENT SERVER</a> to keep in touch with the latest Coteab Macro updates!
            </div>
        </>
    );
}
