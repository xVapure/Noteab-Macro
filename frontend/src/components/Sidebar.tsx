interface SidebarProps {
    activeTab: string;
    onTabChange: (tab: string) => void;
    isGlitching: boolean;
    macroVersion: string;
}
import GlitchOverlay from "./GlitchOverlay";
import { useGlitchText } from "../hooks/useGlitchText";
import { useConfig } from "../contexts/ConfigContext";

const SidebarItem = ({ item, isActive, onClick, isGlitching, locked, customLabel, customIcon }: { item: any; isActive: boolean; onClick: () => void; isGlitching: boolean; locked?: boolean; customLabel?: string; customIcon?: string }) => {
    const label = useGlitchText(customLabel || item.label || "", isGlitching);
    const isDisabled = item.disabled || locked;
    return (
        <div
            className={`sidebar-item ${isActive ? "active" : ""}`}
            onClick={() => !isDisabled && onClick()}
            style={isDisabled ? { opacity: 0.3, cursor: "not-allowed", pointerEvents: "none" } : {}}
            title={locked ? "🔒 Locked" : undefined}
        >
            <span className="icon">
                {locked ? "🔒" : (customIcon ? <img src={customIcon} alt="" style={{width: "18px", height: "18px", objectFit: "contain"}} /> : item.icon)}
            </span>
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
    { id: "status", label: "Status", icon: "⚙️" },
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
    { id: "themedesign", label: "Theme Design", icon: "🎨" },
    { section: "Others" },
    { id: "credits", label: "Credits", icon: "💜" },
    { id: "donations", label: "Donations <3", icon: "💎" },
];

export default function Sidebar({ activeTab, onTabChange, isGlitching, macroVersion }: SidebarProps) {
    const { config } = useConfig();
    const isCustom = config?.selected_theme === 'custom';
    
    const customTitle = (isCustom && config?.custom_macro_title) ? config.custom_macro_title : "Coteab Macro";
    const customVersion = (isCustom && config?.custom_macro_version) ? config.custom_macro_version : (macroVersion || "v?.?.?");

    const title = useGlitchText(customTitle, isGlitching);
    const version = useGlitchText(customVersion, isGlitching);

    const customLabels = isCustom ? (config?.custom_labels || {}) : {};
    const customIcons = isCustom ? (config?.custom_icons || {}) : {};

    return (
        <div className="sidebar" style={{ position: "relative" }}>
            {isGlitching && <GlitchOverlay />}
            <div className="sidebar-brand">
                <h1>{title.split('').map((c, i) => <span key={i} className="title-letter">{c}</span>)}</h1>
                <div className="version">{version.split('').map((c, i) => <span key={i} className={`version-letter ${c === '0' ? 'is-zero' : ''}`}>{c}</span>)}</div>
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
                            customLabel={item.id ? customLabels[item.id] : undefined}
                            customIcon={item.id ? customIcons[item.id] : undefined}
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
