import { useEffect, useState } from "react";

export default function DonationsPage() {
    const [donators, setDonators] = useState<string>("Loading appreciation list...");

    useEffect(() => {
        fetch("https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/appreciation_list.txt")
            .then(res => res.text())
            .then(text => setDonators(text))
            .catch(err => setDonators("Unable to load appreciation list.\n" + err));
    }, []);

    return (
        <>
            <div className="page-header">
                <h2>Donations {"<3"}</h2>
                <p>Support the development of Coteab Macro</p>
            </div>

            <div className="card">
                <div className="card-header">
                    <div className="card-icon">💎</div>
                    <div>
                        <h3>Support Us</h3>
                        <p>Help us keep the project alive</p>
                    </div>
                </div>

                <div style={{ padding: "0 15px 15px 15px", color: "var(--text-secondary)", lineHeight: "1.6" }}>
                    <p style={{ marginBottom: "12px" }}>
                        Our projects are 100% free to use and you're allowed to recycle any fraction of our code with proper credits.
                        However, if you want to support our team, you can help us by purchasing any of the gamepasses below :)
                    </p>
                    <p style={{ marginBottom: "12px" }}>
                        It helps us out a lot mentally, any donations above 100 Robux will get you on the appreciation list below,
                        500 Robux will give you the permission to leave a special message on the appreciation list (must be sfw though)
                        & 1000 Robux will give you access to early Coteab macro releases (beta vers) :D
                    </p>
                    <p style={{ marginBottom: "15px" }}>
                        Normally we will check donations history daily, but if your Roblox username isn't displayed here please DM "@criticize." on Discord.
                        The appreciation list also takes up to 5 minutes to update due to Github.
                    </p>

                    <a
                        href="https://www.roblox.com/games/18203398779/Medival-castle#!/store"
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-accent"
                        style={{
                            width: "100%",
                            justifyContent: "center",
                            fontWeight: "bold",
                            textDecoration: "none",
                            display: "flex",
                            alignItems: "center"
                        }}
                    >
                        Visit Gamepass Store
                    </a>
                    <div style={{ textAlign: "center", marginTop: "8px", fontSize: "12px", opacity: 0.7 }}>
                        https://www.roblox.com/games/18203398779/Medival-castle#!/store
                    </div>
                </div>
            </div>

            <div className="card" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: "300px" }}>
                <div className="card-header">
                    <div className="card-icon">🏆</div>
                    <div>
                        <h3>Donators Hall of Fame</h3>
                        <p>It automatically updates from GitHub</p>
                    </div>
                </div>

                <div style={{ padding: "15px", flex: 1, display: "flex", flexDirection: "column" }}>
                    <textarea
                        readOnly
                        value={donators}
                        style={{
                            flex: 1,
                            width: "100%",
                            resize: "none",
                            backgroundColor: "rgba(0,0,0,0.2)",
                            color: "var(--text-primary)",
                            border: "1px solid var(--border-color)",
                            borderRadius: "8px",
                            padding: "12px",
                            fontFamily: "monospace",
                            fontSize: "13px",
                            lineHeight: "1.5",
                            outline: "none"
                        }}
                    />
                </div>
            </div>
        </>
    );
}
