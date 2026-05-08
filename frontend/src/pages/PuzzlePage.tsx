import { useState, useEffect } from "react";
const PUZZLES = [
    {
        id: 1,
        title: "The Unbreakable Spirit",
        icon: "❓",
        subtitle: "A legendary horse girl who never gave up",
        description: "She shattered her leg not once, but twice. And the world told her it was over..."
            + "But on that cold December day at Nakayama, after 364 days away, she proved them all wrong."
            + "Her idol wore the number 0. She wore the crown nobody believed she could reclaim. "
            + "What is the name of the signature move she does when she's feeling invincible?",
        answer: "teiostep",
        solvedMsg: "The spirit of Teio lives on. First key obtained.",
    },
    {
        id: 2,
        title: "The Last Fragment for the Hunt",
        icon: "❓",
        subtitle: "Numbers hold the final answer.",
        description: "A sequence of numbers was left behind. Each one points to a letter. Decode them and you'll have the final key. "
            + "The hint is somewhere out there... check the Coteab Server on discord!",
        answer: "dawnbreaker",
        solvedMsg: "Fragment decoded. Final key obtained.",
    },
];

function PuzzleCard({ puzzle, solved, onSolve, locked }: {
    puzzle: typeof PUZZLES[0];
    solved: boolean;
    onSolve: () => void;
    locked: boolean;
}) {
    const [input, setInput] = useState("");
    const [feedback, setFeedback] = useState("");
    const [attempts, setAttempts] = useState(0);

    const submit = () => {
        const guess = input.trim().toLowerCase().replace(/\s+/g, "");
        if (!guess) return;
        setAttempts(attempts + 1);

        if (guess === puzzle.answer) {
            setFeedback(puzzle.solvedMsg);
            onSolve();
        } else {
            setFeedback("Wrong answer. Try again!");
        }
        setInput("");
    };

    if (locked) {
        return (
            <div className="card" style={{ opacity: 0.35, pointerEvents: "none" }}>
                <div className="card-header">
                    <div className="card-icon">🔒</div>
                    <div>
                        <h3>{puzzle.title} — LOCKED</h3>
                        <p>Please solve the previous puzzle first!</p>
                    </div>
                </div>
            </div>
        );
    }

    if (solved) {
        return (
            <div className="card">
                <div className="card-header">
                    <div className="card-icon">✅</div>
                    <div>
                        <h3>{puzzle.title} — SOLVED</h3>
                        <p style={{ color: "#4ade80", fontFamily: "monospace", fontSize: "12px" }}>{puzzle.solvedMsg}</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="card">
            <div className="card-header">
                <div className="card-icon" style={{ fontSize: "20px" }}>{puzzle.icon}</div>
                <div>
                    <h3>{puzzle.title}</h3>
                    <p>{puzzle.subtitle}</p>
                </div>
            </div>

            <div style={{ padding: "0 15px 15px" }}>
                <p style={{ color: "var(--text-secondary)", marginBottom: "14px", fontSize: "13px", lineHeight: "1.6" }}>
                    {puzzle.description}
                </p>

                <div style={{ display: "flex", gap: "8px" }}>
                    <input
                        className="form-input"
                        placeholder="answer..."
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && submit()}
                        style={{ flex: 1, fontFamily: "monospace" }}
                    />
                    <button className="btn btn-accent" onClick={submit}>Submit</button>
                </div>

                {feedback && (
                    <div style={{
                        marginTop: "8px",
                        padding: "8px 12px",
                        borderRadius: "6px",
                        fontSize: "12px",
                        color: feedback.includes("obtained") ? "#4ade80" : "#f87171",
                        background: feedback.includes("obtained") ? "rgba(74,222,128,0.1)" : "rgba(248,113,113,0.1)",
                    }}>
                        {feedback}
                    </div>
                )}

                {attempts > 0 && !feedback.includes("obtained") && (
                    <div style={{ marginTop: "6px", fontSize: "11px", opacity: 0.35 }}>
                        attempts: {attempts}
                    </div>
                )}
            </div>
        </div>
    );
}

export default function PuzzlePage() {
    const [solved, setSolved] = useState<Set<number>>(new Set());
    useEffect(() => {
        try {
            const s = localStorage.getItem("puzzle_solved");
            if (s) setSolved(new Set(JSON.parse(s)));
        } catch (_e) { /* ignore */ }
    }, []);

    const solve = (id: number) => {
        const next = new Set(solved);
        next.add(id);
        setSolved(next);
        try { localStorage.setItem("puzzle_solved", JSON.stringify([...next])); } catch (_e) { /* ignore */ }
    };

    const allDone = solved.size === PUZZLES.length;

    return (
        <>
            <div className="page-header">
                <h2 style={{ letterSpacing: "4px" }}>???</h2>
                <p style={{ opacity: 0.5, fontStyle: "italic" }}>
                    {allDone ? "You did it!!!" : "Solve both to earn Akito's respect role ;)"}
                </p>
            </div>

            <div style={{ display: "flex", gap: "6px", marginBottom: "14px", justifyContent: "center" }}>
                {PUZZLES.map(p => (
                    <div key={p.id} style={{
                        width: "10px", height: "10px", borderRadius: "50%",
                        background: solved.has(p.id) ? "#4ade80" : "rgba(255,255,255,0.12)",
                        border: `2px solid ${solved.has(p.id) ? "#4ade80" : "rgba(255,255,255,0.18)"}`,
                    }} />
                ))}
            </div>

            {PUZZLES.map((p, i) => (
                <PuzzleCard
                    key={p.id}
                    puzzle={p}
                    solved={solved.has(p.id)}
                    onSolve={() => solve(p.id)}
                    locked={i > 0 && !solved.has(PUZZLES[i - 1].id)}
                />
            ))}

            {allDone && (
                <div className="card" style={{ textAlign: "center", padding: "24px" }}>
                    <div style={{ fontSize: "40px", marginBottom: "10px" }}>⭐⭐⭐</div>
                    <h3 style={{ color: "var(--accent-color)", marginBottom: "6px" }}>
                        Both puzzles solved
                    </h3>
                    <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginBottom: "14px" }}>
                        Screenshot this and send it to <strong>@akiitosama</strong> on Coteab Development discord server to claim your role
                    </p>
                    <div style={{ fontFamily: "monospace", fontSize: "10px", opacity: 0.3, wordBreak: "break-all" }}>
                        {btoa(Date.now().toString(36) + "-coteab-" + Math.random().toString(36).slice(2, 6))}
                    </div>
                </div>
            )}
        </>
    );
}
