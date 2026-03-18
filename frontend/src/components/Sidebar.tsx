
interface SidebarProps {
    activeTab: string;
    onTabChange: (tab: string) => void;
    isGlitching: boolean;
    macroVersion: string;
}
import GlitchOverlay from "./GlitchOverlay";
import { useGlitchText } from "../hooks/useGlitchText";

const SidebarItem = ({ item, isActive, onClick, isGlitching }: { item: any; isActive: boolean; onClick: () => void; isGlitching: boolean }) => {
    const label = useGlitchText(item.label || "", isGlitching);
    return (
        <div
            className={`sidebar-item ${isActive ? "active" : ""}`}
            onClick={() => !item.disabled && onClick()}
            style={item.disabled ? { opacity: 0.5, cursor: "not-allowed", pointerEvents: "none" } : {}}
        >
            <span className="icon">{item.icon}</span>
            {label}
            {item.disabled && <span style={{ fontSize: "10px", marginLeft: "auto", opacity: 0.7 }}>(WIP)</span>}
        </div>
    );
};

const navItems = [
    { section: "General" },
    { id: "notice", label: "Notice", icon: "📋" },
    { id: "webhook", label: "Webhook", icon: "🔗" },
    { id: "stats", label: "Stats", icon: "📊" },
    { section: "Macro Settings" },
    { id: "misc", label: "Automated actions", icon: "🤖" },
    { id: "calibrations", label: "Macro Calibrations", icon: "🎯" },
    { id: "remoteaccess", label: "Remote Control", icon: "🔑" },
    { section: "Main Features" },
    { id: "fishing", label: "Fishing", icon: "🎣" },
    { id: "merchant", label: "Merchant", icon: "🎭" },
    { id: "autopopbuff", label: "Auto Pop Buff", icon: "🧪" },
    { id: "auras", label: "Auras", icon: "✨" },
    { id: "movements", label: "Movements", icon: "🗺️" },
    { id: "potioncraft", label: "Potion Crafting", icon: "🧪" },
    { id: "otherfeatures", label: "Other Features", icon: "🔧" },
    { id: "customization", label: "Customizations", icon: "🔧" },
    { section: "Others" },
    { id: "credits", label: "Credits", icon: "💜" },
    { id: "donations", label: "Donations <3", icon: "💎" },
];

export default function Sidebar({ activeTab, onTabChange, isGlitching, macroVersion }: SidebarProps) {
    const title = useGlitchText("Coteab Macro", isGlitching);
    const version = useGlitchText(macroVersion || "v?.?.?", isGlitching);
    return (
        <div className="sidebar" style={{ position: "relative" }}>
            {isGlitching && <GlitchOverlay />}
            <div className="sidebar-brand">
                <h1>{title}</h1>
                <div className="version">{version}</div>
            </div>

            <div className="sidebar-nav">
                {navItems.map((item, i) => {
                    if ("section" in item && item.section) {
                        return (
                            <div key={`s-${i}`} className="sidebar-section-label">
                                {item.section}
                            </div>
                        );
                    }
                    return (
                        <SidebarItem
                            key={item.id}
                            item={item}
                            isActive={activeTab === item.id}
                            onClick={() => item.id && onTabChange(item.id)}
                            isGlitching={isGlitching}
                        />
                    );
                })}
            </div>

            <div className="sidebar-footer">
                <div className="by-line">
                    Coteab Macro made by <span>Coteab Development Team</span>
                </div>
            </div>
        </div>
    );
}