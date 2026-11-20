import React, { useState, useEffect, useRef } from "react";
import { useConfig } from "../contexts/ConfigContext";
import NoticePage from "./NoticePage";
import WebhookPage from "./WebhookPage";
import CalibrationPage from "./CalibrationPage";
import MiscPage from "./MiscPage";
import FishingPage from "./FishingPage";
import MerchantPage from "./MerchantPage";
import AutoPopBuffPage from "./AutoPopBuffPage";
import AurasPage from "./AurasPage";
import PotionCraftPage from "./PotionCraftPage";
import StatusPage from "./StatusPage";
import StatsPage from "./StatsPage";
import OtherFeaturesPage from "./OtherFeaturesPage";
import CustomizationPage from "./CustomizationPage";
import MovementsPage from "./MovementsPage";

const pages: Record<string, React.FC> = {
  notice: NoticePage,
  webhook: WebhookPage,
  calibrations: CalibrationPage,
  misc: MiscPage,
  fishing: FishingPage,
  merchant: MerchantPage,
  autopopbuff: AutoPopBuffPage,
  auras: AurasPage,
  movements: MovementsPage,
  potioncraft: PotionCraftPage,
  stats: StatsPage,
  status: StatusPage,
  otherfeatures: OtherFeaturesPage,
  customization: CustomizationPage,
};

// Helper to convert hex + opacity to rgba string
const hexToRgba = (hex: string, alpha: number) => {
    const r = parseInt(hex.slice(1, 3), 16) || 0;
    const g = parseInt(hex.slice(3, 5), 16) || 0;
    const b = parseInt(hex.slice(5, 7), 16) || 0;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

// Helper to extract hex and opacity from an rgba string
const rgbaToHexAndAlpha = (rgbaStr: string) => {
    const match = rgbaStr.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
    if (!match) return { hex: "#0f0f14", alpha: 1 };
    const r = parseInt(match[1]).toString(16).padStart(2, '0');
    const g = parseInt(match[2]).toString(16).padStart(2, '0');
    const b = parseInt(match[3]).toString(16).padStart(2, '0');
    const a = match[4] ? parseFloat(match[4]) : 1;
    return { hex: `#${r}${g}${b}`, alpha: a };
};

const RENAMEABLE_TABS = [
    { id: "notice", label: "Notice" },
    { id: "webhook", label: "Webhook" },
    { id: "stats", label: "Stats" },
    { id: "status", label: "Status" },
    { id: "misc", label: "Automated actions" },
    { id: "calibrations", label: "Macro Calibrations" },
    { id: "remoteaccess", label: "Remote Control" },
    { id: "fishing", label: "Fishing" },
    { id: "merchant", label: "Merchant" },
    { id: "autopopbuff", label: "Auto Pop Buff" },
    { id: "auras", label: "Auras" },
    { id: "movements", label: "Movements" },
    { id: "potioncraft", label: "Potion Crafting" },
    { id: "otherfeatures", label: "Other Features" },
    { id: "customization", label: "Customizations" },
    { id: "themedesign", label: "Theme Design" },
    { id: "credits", label: "Credits" },
    { id: "donations", label: "Donations <3" }
];

export default function ThemeDesignPage() {
    const { config, setConfig, saveConfig } = useConfig();
    const themeReadyRef = useRef(false);
    
    const saved = config?.custom_theme_data;
    const sv = saved?.variables || {} as Record<string, string>;
    
    const parseSavedRgba = (varName: string, defaultHex: string, defaultAlpha: number) => {
        const val = sv[varName];
        if (!val) return { hex: defaultHex, alpha: defaultAlpha };
        if (val.startsWith('#')) return { hex: val, alpha: 1 };
        return rgbaToHexAndAlpha(val);
    };
    
    const savedSidebar = parseSavedRgba('--bg-sidebar', '#0f0f14', 0.3);
    const savedMain = parseSavedRgba('--bg-main', '#0d0d11', 0.8);
    const savedCard = parseSavedRgba('--bg-card', '#15151e', 0.3);

    const [themeName, setThemeName] = useState(saved?.theme_name || "My Custom Theme");
    const [accentColor, setAccentColor] = useState(sv['--accent'] || "#7c5bf5");
    const [bgRoot, setBgRoot] = useState(sv['--bg-root'] || "#09090b");
    const [borderColor, setBorderColor] = useState(sv['--border'] || "#2a2a35");

    const [sidebarHex, setSidebarHex] = useState(savedSidebar.hex);
    const [sidebarAlpha, setSidebarAlpha] = useState(savedSidebar.alpha);

    const [mainHex, setMainHex] = useState(savedMain.hex);
    const [mainAlpha, setMainAlpha] = useState(savedMain.alpha);

    const [cardHex, setCardHex] = useState(savedCard.hex);
    const [cardAlpha, setCardAlpha] = useState(savedCard.alpha);

    const [textPrimary, setTextPrimary] = useState(sv['--text-primary'] || "#e4e4e7");
    const [textSecondary, setTextSecondary] = useState(sv['--text-secondary'] || "#a1a1aa");
    const [bgInput, setBgInput] = useState(sv['--bg-input'] || "#111119");
    const [borderRadiusStr, setBorderRadiusStr] = useState(sv['--radius-md'] || "0px");
    const [successColor, setSuccessColor] = useState(sv['--success'] || "#22c55e");
    const [dangerColor, setDangerColor] = useState(sv['--danger'] || "#ef4444");
    const [warningColor, setWarningColor] = useState(sv['--warning'] || "#f59e0b");
    const [cornerColor, setCornerColor] = useState(sv['--corner-color'] || "#7c5bf5");
    const [sidebarBorderWidth, setSidebarBorderWidth] = useState(sv['--sidebar-border-width'] || "1px");
    
    const [previewTab, setPreviewTab] = useState("auras");

    const [bgType, setBgType] = useState<"solid" | "image" | "gradient">(saved?.bg_type || "solid");
    const [customBgUrl, setCustomBgUrl] = useState(saved?.custom_bg_url || "");
    
    const [grad1, setGrad1] = useState(saved?.grad1 || "#ee7752");
    const [grad2, setGrad2] = useState(saved?.grad2 || "#e73c7e");
    const [grad3, setGrad3] = useState(saved?.grad3 || "#23a6d5");

    const [customCss, setCustomCss] = useState(saved?.raw_custom_css || "");
    const [cssSearch, setCssSearch] = useState("");
    const cssTextareaRef = useRef<HTMLTextAreaElement>(null);

    const doCssSearch = (query: string, forward: boolean, focusTextarea: boolean = true) => {
        if (!query) return;
        if (!cssTextareaRef.current) return;
        const text = customCss.toLowerCase();
        const q = query.toLowerCase();
        
        const start = focusTextarea ? (cssTextareaRef.current.selectionEnd || 0) : 0;
        
        const applySelectionAndScroll = (idx: number) => {
            if (!cssTextareaRef.current) return;
            if (focusTextarea) cssTextareaRef.current.focus();
            cssTextareaRef.current.setSelectionRange(idx, idx + q.length);
            const newlines = (text.substring(0, idx).match(/\n/g) || []).length;
            const scrollPos = (newlines * 15) - (cssTextareaRef.current.clientHeight / 2) + 20;
            cssTextareaRef.current.scrollTop = Math.max(0, scrollPos);
        };
        
        if (!forward) {
            const substr = text.substring(0, cssTextareaRef.current.selectionStart || text.length);
            const index = substr.lastIndexOf(q);
            if (index !== -1) {
                applySelectionAndScroll(index);
            }
        } else {
            const index = text.indexOf(q, start);
            if (index !== -1) {
                applySelectionAndScroll(index);
            } else if (focusTextarea) {
                const wrapIndex = text.indexOf(q, 0);
                if (wrapIndex !== -1) {
                    applySelectionAndScroll(wrapIndex);
                }
            }
        }
    };

    const handleCssSearch = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter" && cssSearch) {
            e.preventDefault();
            doCssSearch(cssSearch, !e.shiftKey, true);
        }
    };
    const [fontUrl, setFontUrl] = useState(saved?.raw_font_url || "");
    const [fontWeight, setFontWeight] = useState(saved?.font_weight || "normal");
    const [fontStyle, setFontStyle] = useState(saved?.font_style || "normal");
    
    const [customTitle, setCustomTitle] = useState(saved?.custom_macro_title || "");
    const [customVersion, setCustomVersion] = useState(saved?.custom_macro_version || "");

    const [customLabels, setCustomLabels] = useState<Record<string, string>>(saved?.custom_labels || {});
    const [customIcons, setCustomIcons] = useState<Record<string, string>>(saved?.custom_icons || {});

    const [hoveredSelector, setHoveredSelector] = useState<string | null>(null);

    const handleFileToB64 = (e: React.ChangeEvent<HTMLInputElement>, callback: (b64: string) => void) => {
        const file = e.target.files?.[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (event) => {
            const b64 = event.target?.result as string;
            callback(b64);
        };
        reader.readAsDataURL(file);
    };

    const [appCssRules, setAppCssRules] = useState<{selector: string, cssText: string}[]>([]);

    // Skip computed styles if saved config exists (state already initialized above)
    useEffect(() => {
        if (saved?.variables && Object.keys(saved.variables).length > 0) {
            // CSS rules for explorer still need loading
        } else {
            const target = document.body;
            setAccentColor(getComputedStyle(target).getPropertyValue('--accent').trim() || "#7c5bf5");
            setBgRoot(getComputedStyle(target).getPropertyValue('--bg-root').trim() || "#09090b");
            setBorderColor(getComputedStyle(target).getPropertyValue('--border').trim() || "#2a2a35");

            const sb = getComputedStyle(target).getPropertyValue('--bg-sidebar').trim();
            if (sb.startsWith('#')) { setSidebarHex(sb); setSidebarAlpha(1); }
            else { const parsed = rgbaToHexAndAlpha(sb); setSidebarHex(parsed.hex); setSidebarAlpha(parsed.alpha); }

            const mn = getComputedStyle(target).getPropertyValue('--bg-main').trim();
            if (mn.startsWith('#')) { setMainHex(mn); setMainAlpha(1); }
            else { const parsed = rgbaToHexAndAlpha(mn); setMainHex(parsed.hex); setMainAlpha(parsed.alpha); }

            const cd = getComputedStyle(target).getPropertyValue('--bg-card').trim();
            if (cd.startsWith('#')) { setCardHex(cd); setCardAlpha(1); }
            else { const parsed = rgbaToHexAndAlpha(cd); setCardHex(parsed.hex); setCardAlpha(parsed.alpha); }
        }
        // Also parse document stylesheets for the CSS Explorer
        try {
            const rules: {selector: string, cssText: string}[] = [];
            for (let i = 0; i < document.styleSheets.length; i++) {
                const sheet = document.styleSheets[i];
                try {
                    for (let j = 0; j < sheet.cssRules.length; j++) {
                        const rule = sheet.cssRules[j] as CSSStyleRule;
                        if (rule.selectorText && !rule.selectorText.includes('themeBgGradient') && !rule.selectorText.includes('ThemeCustomFont')) {
                            let text = rule.cssText;
                            rules.push({ selector: rule.selectorText, cssText: text });
                        }
                    }
                } catch(e) { /* ignore cross-origin stylesheets */ }
            }
            const uniqueRules = Array.from(new Map(rules.map(r => [r.selector, r])).values())
                .sort((a,b) => a.selector.localeCompare(b.selector));
            setAppCssRules(uniqueRules);
        } catch(e) {}
    }, []);

    const updateVariable = (variable: string, value: string) => {
        document.body.style.setProperty(variable, value);
    };

    const generateThemeData = () => {
        const accentGlow = hexToRgba(accentColor, 0.15);
        
        const themeConfig: Record<string, string> = {
            "--accent": accentColor,
            "--accent-glow": accentGlow,
            "--accent-text": accentColor,
            "--bg-root": bgRoot,
            "--border": borderColor,
            "--bg-sidebar": hexToRgba(sidebarHex, sidebarAlpha),
            "--bg-main": hexToRgba(mainHex, mainAlpha),
            "--bg-card": hexToRgba(cardHex, cardAlpha),
            "--bg-input": bgInput,
            "--text-primary": textPrimary,
            "--text-secondary": textSecondary,
            "--radius-sm": borderRadiusStr,
            "--radius-md": borderRadiusStr,
            "--radius-lg": borderRadiusStr,
            "--radius-xl": borderRadiusStr,
            "--success": successColor,
            "--danger": dangerColor,
            "--warning": warningColor,
            "--corner-color": cornerColor,
            "--sidebar-border-width": sidebarBorderWidth,
            "--custom-bg-img": "none",
            "--bg-size": "cover",
            "--bg-animation": "none"
        };

        if (bgType === 'image') {
            themeConfig["--custom-bg-img"] = customBgUrl.trim() ? `url('${customBgUrl}')` : 'none';
        } else if (bgType === 'gradient') {
            themeConfig["--custom-bg-img"] = `linear-gradient(-45deg, ${grad1}, ${grad2}, ${grad3})`;
            themeConfig["--bg-size"] = "400% 400%";
            themeConfig["--bg-animation"] = "themeBgGradient 15s ease infinite";
        }

        let finalCss = customCss;
        if (fontUrl.trim()) {
            finalCss = `@font-face {
    font-family: 'ThemeCustomFont';
    src: url('${fontUrl.trim()}');
}
body, * {
    font-family: 'ThemeCustomFont', sans-serif !important;
    font-weight: ${fontWeight} !important;
    font-style: ${fontStyle} !important;
}
` + finalCss;
        }

        return {
            "theme_name": themeName.trim() || "My Custom Theme",
            "variables": themeConfig,
            "custom_css": finalCss,
            "raw_custom_css": customCss,
            "raw_font_url": fontUrl,
            "font_weight": fontWeight,
            "font_style": fontStyle,
            "custom_labels": customLabels,
            "custom_icons": customIcons,
            "custom_macro_title": customTitle,
            "custom_macro_version": customVersion,
            "bg_type": bgType,
            "custom_bg_url": customBgUrl,
            "grad1": grad1,
            "grad2": grad2,
            "grad3": grad3
        };
    };

    useEffect(() => {
        if (!config) return;
        if (!themeReadyRef.current) {
            themeReadyRef.current = true;
            return;
        }
        if (config?.selected_theme === 'custom') {
            updateVariable('--accent', accentColor);
            updateVariable('--bg-root', bgRoot);
            updateVariable('--border', borderColor);
        
        const sbRgba = hexToRgba(sidebarHex, sidebarAlpha);
        updateVariable('--bg-sidebar', sbRgba);

        const mnRgba = hexToRgba(mainHex, mainAlpha);
        updateVariable('--bg-main', mnRgba);
        
        const cdRgba = hexToRgba(cardHex, cardAlpha);
        updateVariable('--bg-card', cdRgba);

        updateVariable('--bg-input', bgInput);
        updateVariable('--text-primary', textPrimary);
        updateVariable('--text-secondary', textSecondary);
        updateVariable('--radius-sm', borderRadiusStr);
        updateVariable('--radius-md', borderRadiusStr);
        updateVariable('--radius-lg', borderRadiusStr);
        updateVariable('--radius-xl', borderRadiusStr);
        
        updateVariable('--success', successColor);
        updateVariable('--danger', dangerColor);
        updateVariable('--warning', warningColor);
        updateVariable('--corner-color', cornerColor);
        updateVariable('--sidebar-border-width', sidebarBorderWidth);

        updateVariable('--accent-glow', hexToRgba(accentColor, 0.15));
        updateVariable('--accent-text', accentColor);

        if (bgType === 'solid') {
            updateVariable('--custom-bg-img', 'none');
            updateVariable('--bg-size', 'cover');
            updateVariable('--bg-animation', 'none');
        } else if (bgType === 'image') {
            const formatted = customBgUrl.trim() ? `url('${customBgUrl}')` : 'none';
            updateVariable('--custom-bg-img', formatted);
            updateVariable('--bg-size', 'cover');
            updateVariable('--bg-animation', 'none');
        } else if (bgType === 'gradient') {
            const gradientCss = `linear-gradient(-45deg, ${grad1}, ${grad2}, ${grad3})`;
            updateVariable('--custom-bg-img', gradientCss);
            updateVariable('--bg-size', '400% 400%');
            updateVariable('--bg-animation', 'themeBgGradient 15s ease infinite');
        }
        }
        let timerId: ReturnType<typeof setTimeout>;
        if (config) {
            const newConfig = { 
                ...config, 
                custom_labels: customLabels, 
                custom_icons: customIcons,
                custom_macro_title: customTitle,
                custom_macro_version: customVersion,
                custom_theme_data: generateThemeData()
            };
            
            timerId = setTimeout(() => {
                setConfig(newConfig);
                saveConfig(newConfig);
            }, 600);
        }

        return () => {
            if (timerId) clearTimeout(timerId);
        };

    }, [accentColor, bgRoot, borderColor, sidebarHex, sidebarAlpha, mainHex, mainAlpha, cardHex, cardAlpha, textPrimary, textSecondary, bgInput, borderRadiusStr, successColor, dangerColor, warningColor, cornerColor, sidebarBorderWidth, bgType, customBgUrl, grad1, grad2, grad3, customLabels, customIcons, customTitle, customVersion, customCss, fontUrl, fontWeight, fontStyle, themeName]);

    const exportTheme = () => {
        const exportData = generateThemeData();

        const safeFilename = (themeName.trim() || "coteab_theme").toLowerCase().replace(/[^a-z0-9_-]/g, '_') + ".json";

        if ((window as any).pywebview?.api?.export_theme) {
            (window as any).pywebview.api.export_theme(exportData, safeFilename)
                .then((res: any) => {
                    if (res.success) {
                        alert(`Theme successfully exported to:\n${res.path}`);
                    } else if (res.error !== 'Cancelled') {
                        alert(`Failed to export theme:\n${res.error}`);
                    }
                });
        } else {
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportData, null, 4));
            const downloadAnchorNode = document.createElement('a');
            downloadAnchorNode.setAttribute("href", dataStr);
            downloadAnchorNode.setAttribute("download", safeFilename);
            document.body.appendChild(downloadAnchorNode);
            downloadAnchorNode.click();
            downloadAnchorNode.remove();
        }
    };

    return (
        <div className="card">
            {hoveredSelector && (
                <style id="css-explorer-highlight">
                    {`
                    ${hoveredSelector} {
                        outline: 3px dashed var(--accent) !important;
                        outline-offset: -3px !important;
                        background-color: rgba(124, 91, 245, 0.2) !important;
                        transition: all 0.2s ease !important;
                        z-index: 9999 !important;
                    }
                    `}
                </style>
            )}
            {config?.selected_theme === 'custom' && (
                <style>{`
                    @keyframes themeBgGradient {
                        0% { background-position: 0% 50%; }
                        50% { background-position: 100% 50%; }
                        100% { background-position: 0% 50%; }
                    }
                    ${fontUrl.trim() ? `
                    @font-face {
                        font-family: 'ThemeCustomFontPreview';
                        src: url('${fontUrl.trim()}');
                    }
                    body, * {
                        font-family: 'ThemeCustomFontPreview', sans-serif !important;
                    }
                    ` : ''}
                `}</style>
            )}
            
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: 600 }}>Theme Designer</h3>
            </div>
            <p style={{ color: "var(--text-secondary)", marginBottom: "20px", fontSize: "13px" }}>
                Design your custom Coteab Macro theme! The colors will update in real-time. Export the theme to save it!
            </p>

            <div style={{ display: "grid", gap: "20px", marginBottom: "25px" }}>
                
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Theme Name</label>
                    <input type="text" value={themeName} onChange={(e) => setThemeName(e.target.value)} placeholder="My Awesome Theme" style={{ width: "100%", height: "35px", background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-primary)", padding: "0 10px" }} />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "10px", padding: "15px", background: "var(--bg-card-hover)", borderRadius: "6px" }}>
                    <label style={{ fontSize: "13px", fontWeight: "bold", color: "var(--text-primary)" }}>Advanced Colors & Elements</label>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Primary Text Color</label>
                            <input type="color" value={textPrimary} onChange={(e) => setTextPrimary(e.target.value)} style={{ width: "100%", height: "35px", cursor: "pointer", border: "1px solid var(--border)", borderRadius: "4px" }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Secondary Text Color</label>
                            <input type="color" value={textSecondary} onChange={(e) => setTextSecondary(e.target.value)} style={{ width: "100%", height: "35px", cursor: "pointer", border: "1px solid var(--border)", borderRadius: "4px" }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Input Field Background</label>
                            <input type="color" value={bgInput} onChange={(e) => setBgInput(e.target.value)} style={{ width: "100%", height: "35px", cursor: "pointer", border: "1px solid var(--border)", borderRadius: "4px" }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Global Border Radius</label>
                            <input type="text" value={borderRadiusStr} onChange={(e) => setBorderRadiusStr(e.target.value)} placeholder="0px or 8px" style={{ width: "100%", height: "35px", background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-primary)", padding: "0 10px" }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Success Status Color (Green)</label>
                            <input type="color" value={successColor} onChange={(e) => setSuccessColor(e.target.value)} style={{ width: "100%", height: "35px", cursor: "pointer", border: "1px solid var(--border)", borderRadius: "4px" }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Danger Status Color (Red)</label>
                            <input type="color" value={dangerColor} onChange={(e) => setDangerColor(e.target.value)} style={{ width: "100%", height: "35px", cursor: "pointer", border: "1px solid var(--border)", borderRadius: "4px" }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Warning Status Color (Yellow)</label>
                            <input type="color" value={warningColor} onChange={(e) => setWarningColor(e.target.value)} style={{ width: "100%", height: "35px", cursor: "pointer", border: "1px solid var(--border)", borderRadius: "4px" }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Window Corner Brackets Color</label>
                            <input type="color" value={cornerColor} onChange={(e) => setCornerColor(e.target.value)} style={{ width: "100%", height: "35px", cursor: "pointer", border: "1px solid var(--border)", borderRadius: "4px" }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Sidebar Divider Border Width</label>
                            <select value={sidebarBorderWidth} onChange={(e) => setSidebarBorderWidth(e.target.value)} style={{ width: "100%", height: "35px", background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-primary)", padding: "0 10px" }}>
                                <option value="0px">Hidden (0px)</option>
                                <option value="1px">Thin (1px)</option>
                                <option value="2px">Thick (2px)</option>
                            </select>
                        </div>
                    </div>
                </div>


                <div style={{ display: "flex", flexDirection: "column", gap: "10px", padding: "15px", background: "var(--bg-card-hover)", borderRadius: "6px" }}>
                    <label style={{ fontSize: "13px", fontWeight: "bold", color: "var(--text-primary)" }}>App Background</label>
                    
                    <select value={bgType} onChange={(e) => setBgType(e.target.value as any)} style={{ width: "100%", height: "35px", background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-primary)", padding: "0 10px" }}>
                        <option value="solid">Solid Color (Uses Main Background Color)</option>
                        <option value="image">Custom Image URL</option>
                        <option value="gradient">Animated Gradient</option>
                    </select>

                    {bgType === "solid" && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginTop: "10px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Main Background Color</label>
                            <input type="color" value={bgRoot} onChange={(e) => setBgRoot(e.target.value)} style={{ width: "100%", height: "35px", border: "none", borderRadius: "4px", cursor: "pointer", background: "transparent" }} />
                        </div>
                    )}

                    {bgType === "image" && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginTop: "10px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Custom Image URL</label>
                            <input type="text" placeholder="https://example.com/image.png" value={customBgUrl} onChange={(e) => setCustomBgUrl(e.target.value)} style={{ width: "100%", height: "35px", background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-primary)", padding: "0 10px" }} />
                        </div>
                    )}

                    {bgType === "gradient" && (
                        <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "5px" }}>
                                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Color 1</label>
                                <input type="color" value={grad1} onChange={(e) => setGrad1(e.target.value)} style={{ width: "100%", height: "35px", border: "none", borderRadius: "4px", cursor: "pointer", background: "transparent" }} />
                            </div>
                            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "5px" }}>
                                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Color 2</label>
                                <input type="color" value={grad2} onChange={(e) => setGrad2(e.target.value)} style={{ width: "100%", height: "35px", border: "none", borderRadius: "4px", cursor: "pointer", background: "transparent" }} />
                            </div>
                            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "5px" }}>
                                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Color 3</label>
                                <input type="color" value={grad3} onChange={(e) => setGrad3(e.target.value)} style={{ width: "100%", height: "35px", border: "none", borderRadius: "4px", cursor: "pointer", background: "transparent" }} />
                            </div>
                        </div>
                    )}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Accent Color</label>
                    <input type="color" value={accentColor} onChange={(e) => setAccentColor(e.target.value)} style={{ width: "100%", height: "35px", border: "none", borderRadius: "4px", cursor: "pointer", background: "transparent" }} />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                    <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Border Color</label>
                    <input type="color" value={borderColor} onChange={(e) => setBorderColor(e.target.value)} style={{ width: "100%", height: "35px", border: "none", borderRadius: "4px", cursor: "pointer", background: "transparent" }} />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Sidebar Color</label>
                        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Opacity: {Math.round(sidebarAlpha * 100)}%</span>
                    </div>
                    <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                        <input type="color" value={sidebarHex} onChange={(e) => setSidebarHex(e.target.value)} style={{ flex: "0 0 50px", height: "35px", border: "none", borderRadius: "4px", cursor: "pointer", background: "transparent" }} />
                        <input type="range" min="0" max="1" step="0.05" value={sidebarAlpha} onChange={(e) => setSidebarAlpha(parseFloat(e.target.value))} style={{ flex: 1 }} />
                    </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Main Content Area Color</label>
                        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Opacity: {Math.round(mainAlpha * 100)}%</span>
                    </div>
                    <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                        <input type="color" value={mainHex} onChange={(e) => setMainHex(e.target.value)} style={{ flex: "0 0 50px", height: "35px", border: "none", borderRadius: "4px", cursor: "pointer", background: "transparent" }} />
                        <input type="range" min="0" max="1" step="0.05" value={mainAlpha} onChange={(e) => setMainAlpha(parseFloat(e.target.value))} style={{ flex: 1 }} />
                    </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Card Color</label>
                        <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Opacity: {Math.round(cardAlpha * 100)}%</span>
                    </div>
                    <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                        <input type="color" value={cardHex} onChange={(e) => setCardHex(e.target.value)} style={{ flex: "0 0 50px", height: "35px", border: "none", borderRadius: "4px", cursor: "pointer", background: "transparent" }} />
                        <input type="range" min="0" max="1" step="0.05" value={cardAlpha} onChange={(e) => setCardAlpha(parseFloat(e.target.value))} style={{ flex: 1 }} />
                    </div>
                </div>


                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "15px", background: "var(--bg-main)", padding: "15px", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <label style={{ fontSize: "13px", fontWeight: "bold", color: "var(--text-primary)" }}>Labels, Fonts & Branding</label>
                    
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Macro Title</label>
                            <input 
                                type="text" 
                                value={customTitle} 
                                onChange={(e) => setCustomTitle(e.target.value)}
                                placeholder="Coteab Macro"
                                style={{ width: "100%", height: "30px", background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-primary)", padding: "0 10px" }}
                            />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                            <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Macro Version text</label>
                            <input 
                                type="text" 
                                value={customVersion} 
                                onChange={(e) => setCustomVersion(e.target.value)}
                                placeholder="v2.1.8-hotfix1"
                                style={{ width: "100%", height: "30px", background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-primary)", padding: "0 10px" }}
                            />
                        </div>
                    </div>
                    
                    <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                        <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Custom Font File (.ttf or .woff)</label>
                        <div style={{ display: "flex", gap: "5px", alignItems: "center" }}>
                            <input 
                                type="file" 
                                accept=".ttf,.woff,.woff2"
                                onChange={(e) => handleFileToB64(e, setFontUrl)}
                                style={{ width: "100%", height: "30px", fontSize: "11px", color: "var(--text-secondary)" }}
                            />
                            {fontUrl && <button onClick={() => setFontUrl("")} style={{ background: "transparent", border: "1px solid var(--border)", color: "var(--text-secondary)", borderRadius: "4px", padding: "4px 8px", cursor: "pointer", fontSize: "11px" }}>Clear</button>}
                        </div>
                        <div style={{ display: "flex", gap: "10px", marginTop: "5px" }}>
                            <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "4px" }}>
                                <input type="checkbox" checked={fontWeight === "bold"} onChange={(e) => setFontWeight(e.target.checked ? "bold" : "normal")} /> Bold
                            </label>
                            <label style={{ fontSize: "11px", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "4px" }}>
                                <input type="checkbox" checked={fontStyle === "italic"} onChange={(e) => setFontStyle(e.target.checked ? "italic" : "normal")} /> Italic
                            </label>
                        </div>
                    </div>

                    <label style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "10px" }}>Rename Sidebar Tabs & Icons</label>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
                        {RENAMEABLE_TABS.map(tab => (
                            <div key={tab.id} style={{ display: "flex", flexDirection: "column", gap: "3px", background: "rgba(0,0,0,0.2)", padding: "8px", borderRadius: "4px" }}>
                                <span style={{ fontSize: "10px", color: "var(--text-secondary)", fontWeight: "bold" }}>{tab.label}</span>
                                <input 
                                    type="text" 
                                    value={customLabels[tab.id] || ""} 
                                    onChange={(e) => setCustomLabels({...customLabels, [tab.id]: e.target.value})}
                                    placeholder={tab.label}
                                    style={{ width: "100%", height: "28px", background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-primary)", padding: "0 8px", fontSize: "11px", marginBottom: "3px" }}
                                />
                                <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                                    <span style={{ fontSize: "9px", color: "var(--text-secondary)" }}>Icon:</span>
                                    <input 
                                        type="file" 
                                        accept="image/png, image/jpeg, image/gif, image/webp"
                                        onChange={(e) => handleFileToB64(e, (b64) => setCustomIcons({...customIcons, [tab.id]: b64}))}
                                        style={{ fontSize: "9px", width: "110px", color: "var(--text-secondary)" }}
                                    />
                                    {customIcons[tab.id] && <img src={customIcons[tab.id]} alt="" style={{width: "14px", height: "14px", objectFit: "contain", background: "var(--bg-input)", borderRadius: "2px", padding: "1px"}} />}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginTop: "10px", background: "var(--bg-main)", padding: "15px", borderRadius: "6px", border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <label style={{ fontSize: "14px", fontWeight: "bold", color: "var(--accent)" }}>Advanced CSS Designer</label>
                    </div>

                    <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                        You can live-preview pages while writing custom CSS here to change specific elements like buttons, cards, and borders!
                    </p>


                    <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "10px", marginBottom: "10px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                            <select 
                                value={previewTab} 
                                onChange={(e) => setPreviewTab(e.target.value)}
                                style={{ background: "var(--bg-input)", color: "var(--text-primary)", border: "1px solid var(--border)", padding: "4px 8px", borderRadius: "4px", fontSize: "11px" }}
                            >
                                {RENAMEABLE_TABS.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
                            </select>
                        </div>
                        <div style={{ padding: "10px", background: "var(--bg-root)", borderRadius: "var(--radius-md)", height: "300px", overflowY: "auto", border: "1px dashed var(--border)" }}>
                            <div style={{ pointerEvents: "none", userSelect: "none", opacity: 0.9 }}>
                                {pages[previewTab] ? React.createElement(pages[previewTab]) : <p>Select a page to preview</p>}
                            </div>
                        </div>
                    </div>

                    <details style={{ fontSize: "11px", color: "var(--text-secondary)", background: "var(--bg-card)", padding: "8px", borderRadius: "4px", marginBottom: "5px" }}>
                        <summary style={{ cursor: "pointer", fontWeight: "bold", color: "var(--text-primary)" }}>🔍 Browse Live App CSS Structure (Click to copy)</summary>
                        <p style={{ marginTop: "8px", marginBottom: "8px", color: "var(--text-secondary)" }}>
                            Click on any class below to see its current properties.
                        </p>
                        <div style={{ maxHeight: "250px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "4px", paddingRight: "5px", userSelect: "text" }}>
                            {appCssRules.map((rule, idx) => (
                                <details 
                                    key={idx} 
                                    style={{ background: "var(--bg-input)", padding: "4px 8px", borderRadius: "4px" }}
                                    onMouseEnter={() => setHoveredSelector(rule.selector)}
                                    onMouseLeave={() => setHoveredSelector(null)}
                                >
                                    <summary style={{ cursor: "pointer", fontFamily: "monospace", color: "var(--accent)", userSelect: "text" }}>{rule.selector}</summary>
                                    <pre style={{ margin: "5px 0 0 0", color: "var(--text-secondary)", whiteSpace: "pre-wrap", wordBreak: "break-all", userSelect: "text" }}>
                                        {rule.cssText}
                                    </pre>
                                </details>
                            ))}
                            {appCssRules.length === 0 && <span>Loading CSS...</span>}
                        </div>
                    </details>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "5px" }}>
                        <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "10px" }}>
                            Custom CSS Code
                            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                                <input 
                                    type="text"
                                    placeholder="Search..."
                                    value={cssSearch}
                                    onChange={(e) => {
                                        setCssSearch(e.target.value);
                                        doCssSearch(e.target.value, true, false);
                                    }}
                                    onKeyDown={handleCssSearch}
                                    style={{ width: "120px", height: "24px", background: "var(--bg-input)", border: "1px solid var(--border)", borderRadius: "4px", color: "var(--text-primary)", padding: "0 8px", fontSize: "11px", fontWeight: "normal" }}
                                />
                                <button onClick={() => doCssSearch(cssSearch, false, true)} style={{ background: "var(--bg-input)", border: "1px solid var(--border)", color: "var(--text-primary)", borderRadius: "4px", padding: "2px 6px", cursor: "pointer", fontSize: "10px" }}>▲</button>
                                <button onClick={() => doCssSearch(cssSearch, true, true)} style={{ background: "var(--bg-input)", border: "1px solid var(--border)", color: "var(--text-primary)", borderRadius: "4px", padding: "2px 6px", cursor: "pointer", fontSize: "10px" }}>▼</button>
                            </div>
                        </label>
                        <select 
                            onChange={(e) => {
                                if (e.target.value) {
                                    setCustomCss(customCss + "\n\n" + e.target.value);
                                    e.target.value = "";
                                }
                            }}
                            style={{ background: "var(--accent)", color: "#fff", border: "none", padding: "4px 8px", borderRadius: "4px", fontSize: "11px", cursor: "pointer" }}
                        >
                            <option value="">+ Add CSS Snippet Template...</option>
                            <option value={`.card {\n  background: rgba(20, 20, 30, 0.2) !important;\n  backdrop-filter: blur(10px);\n  border: 1px solid rgba(255, 255, 255, 0.1);\n}`}>Glassmorphism Cards</option>
                            <option value={`.btn-start {\n  box-shadow: 0 0 15px var(--accent);\n  animation: pulse 2s infinite;\n}\n@keyframes pulse {\n  0% { transform: scale(1); }\n  50% { transform: scale(1.05); }\n  100% { transform: scale(1); }\n}`}>Neon Pulsing Start Button</option>
                            <option value={`.sidebar-item:hover {\n  background: linear-gradient(90deg, var(--accent), transparent) !important;\n  padding-left: 20px;\n  transition: 0.3s;\n}`}>Animated Sidebar Hover</option>
                            <option value={`.form-input, .btn {\n  border-radius: 50px !important;\n}`}>Ultra Rounded Inputs & Buttons</option>
                            <option value={`.sidebar-brand h1 {\n  display: none;\n}`}>Hide Macro Title (Brand)</option>
                            <option value={`::-webkit-scrollbar {\n  width: 8px;\n}\n::-webkit-scrollbar-thumb {\n  background: var(--accent);\n  border-radius: 4px;\n}`}>Custom Scrollbar</option>
                            <option value={`.btn:hover {\n  transform: translateY(-2px);\n  box-shadow: 0 5px 15px rgba(0,0,0,0.5);\n  transition: 0.2s;\n}`}>Float Buttons on Hover</option>
                            <option value={`.card {\n  border: 1px solid var(--accent) !important;\n  box-shadow: 0 0 8px rgba(124, 91, 245, 0.2);\n}`}>Accent Border on Cards</option>
                            <option value={`.sidebar {\n  background: transparent !important;\n  border-right: none !important;\n}`}>Transparent Sidebar</option>
                            <option value={`.sidebar-item.active {\n  background: var(--accent) !important;\n  color: #fff !important;\n  border-radius: 8px;\n}`}>Solid Active Tab</option>
                            <option value={`.sidebar-item.active::before {\n  display: none;\n}`}>Remove Active Tab Indicator Bar</option>
                            <option value={`.header-bar {\n  background: transparent !important;\n  border-bottom: none !important;\n}`}>Transparent Header Bar</option>
                            <option value={`.sidebar-brand {\n  text-align: center;\n  border-bottom: none !important;\n}`}>Centered Brand Title</option>
                            <option value={`.form-input:focus {\n  border-color: var(--accent) !important;\n  box-shadow: 0 0 0 3px rgba(124, 91, 245, 0.25);\n  outline: none;\n}`}>Glow on Input Focus</option>
                            <option value={`.toggle-track {\n  width: 50px !important;\n  height: 26px !important;\n  border-radius: 13px !important;\n}\n.toggle-thumb {\n  width: 22px !important;\n  height: 22px !important;\n  border-radius: 50% !important;\n}`}>Bigger Toggle Switches</option>
                            <option value={`.card {\n  transition: transform 0.2s, box-shadow 0.2s;\n}\n.card:hover {\n  transform: scale(1.01);\n  box-shadow: 0 4px 20px rgba(0,0,0,0.4);\n}`}>Card Hover Lift</option>
                            <option value={`.sidebar-section-label {\n  display: none;\n}`}>Hide Sidebar Section Labels</option>
                            <option value={`.sidebar-item .icon {\n  font-size: 18px;\n}\n.sidebar-item {\n  font-size: 14px;\n  padding: 12px 14px;\n}`}>Bigger Sidebar Items</option>
                            <option value={`.window-frame {\n  border: none !important;\n}\n.corner-bracket {\n  display: none !important;\n}`}>Remove Window Frame & Brackets</option>
                            <option value={`.btn-start {\n  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;\n  border: none !important;\n  color: #fff !important;\n}`}>Gradient Start Button</option>
                            <option value={`.sidebar-brand h1 {\n  background: linear-gradient(90deg, #f093fb, #f5576c, #4facfe) !important;\n  -webkit-background-clip: text !important;\n  -webkit-text-fill-color: transparent !important;\n  background-clip: text !important;\n}`}>Rainbow Brand Title</option>
                        </select>
                    </div>

                    <textarea 
                        ref={cssTextareaRef}
                        value={customCss} 
                        onChange={(e) => setCustomCss(e.target.value)}
                        placeholder="/* Add any custom CSS here to completely change the layout! */&#10;.btn-start {&#10;   border-radius: 50px !important;&#10;}"
                        style={{ width: "100%", height: "200px", background: "var(--bg-input)", border: "1px solid var(--accent)", borderRadius: "4px", color: "var(--text-primary)", padding: "10px", fontFamily: "monospace", fontSize: "12px", resize: "vertical" }}
                    />
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                    <button 
                        className="btn btn-start" 
                        onClick={exportTheme}
                        style={{ flex: 1, height: "40px", fontSize: "14px", fontWeight: "bold", background: "var(--accent)" }}
                    >
                        Export Theme File
                    </button>
                    <button 
                        className="btn" 
                        onClick={() => {
                            const input = document.createElement('input');
                            input.type = 'file';
                            input.accept = '.json';
                            input.onchange = (e) => {
                                const file = (e.target as HTMLInputElement).files?.[0];
                                if (!file) return;
                                const reader = new FileReader();
                                reader.onload = (ev) => {
                                    try {
                                        const data = JSON.parse(ev.target?.result as string);
                                        if ('theme_name' in data) setThemeName(data.theme_name || "My Custom Theme");
                                        if ('raw_custom_css' in data) setCustomCss(data.raw_custom_css || "");
                                        if ('raw_font_url' in data) setFontUrl(data.raw_font_url || "");
                                        if ('font_weight' in data) setFontWeight(data.font_weight || "normal");
                                        if ('font_style' in data) setFontStyle(data.font_style || "normal");
                                        if ('custom_labels' in data) setCustomLabels(data.custom_labels || {});
                                        if ('custom_icons' in data) setCustomIcons(data.custom_icons || {});
                                        if ('custom_macro_title' in data) setCustomTitle(data.custom_macro_title || "");
                                        if ('custom_macro_version' in data) setCustomVersion(data.custom_macro_version || "");
                                        if ('bg_type' in data) setBgType(data.bg_type || "solid");
                                        if ('custom_bg_url' in data) setCustomBgUrl(data.custom_bg_url || "");
                                        if ('grad1' in data) setGrad1(data.grad1 || "#ee7752");
                                        if ('grad2' in data) setGrad2(data.grad2 || "#e73c7e");
                                        if ('grad3' in data) setGrad3(data.grad3 || "#23a6d5");
                                        
                                        if (data.variables) {
                                            const v = data.variables;
                                            if (v['--accent']) setAccentColor(v['--accent']);
                                            if (v['--bg-root']) setBgRoot(v['--bg-root']);
                                            if (v['--border']) setBorderColor(v['--border']);
                                            
                                            if (v['--bg-input']) setBgInput(v['--bg-input']);
                                            if (v['--text-primary']) setTextPrimary(v['--text-primary']);
                                            if (v['--text-secondary']) setTextSecondary(v['--text-secondary']);
                                            if (v['--radius-md']) setBorderRadiusStr(v['--radius-md']);
                                            
                                            if (v['--success']) setSuccessColor(v['--success']);
                                            if (v['--danger']) setDangerColor(v['--danger']);
                                            if (v['--warning']) setWarningColor(v['--warning']);
                                            if (v['--corner-color']) setCornerColor(v['--corner-color']);
                                            if (v['--sidebar-border-width']) setSidebarBorderWidth(v['--sidebar-border-width']);
                                            
                                            if (v['--bg-sidebar']) {
                                                const parsed = rgbaToHexAndAlpha(v['--bg-sidebar']);
                                                setSidebarHex(parsed.hex); setSidebarAlpha(parsed.alpha);
                                            }
                                            if (v['--bg-main']) {
                                                const parsed = rgbaToHexAndAlpha(v['--bg-main']);
                                                setMainHex(parsed.hex); setMainAlpha(parsed.alpha);
                                            }
                                            if (v['--bg-card']) {
                                                const parsed = rgbaToHexAndAlpha(v['--bg-card']);
                                                setCardHex(parsed.hex); setCardAlpha(parsed.alpha);
                                            }

                                            // apply all CSS variables
                                            Object.entries(v).forEach(([key, val]) => {
                                                document.body.style.setProperty(key, val as string);
                                            });
                                        }
                                        
                                        if (config) {
                                            const importedConfig = {
                                                ...config,
                                                custom_labels: data.custom_labels || customLabels,
                                                custom_icons: data.custom_icons || customIcons,
                                                custom_macro_title: data.custom_macro_title || customTitle,
                                                custom_macro_version: data.custom_macro_version || customVersion,
                                                custom_theme_data: data
                                            };
                                            setConfig(importedConfig);
                                            saveConfig(importedConfig);
                                        }
                                        
                                        alert("Theme imported successfully!");
                                    } catch(e) {
                                        alert("Invalid theme file! Make sure it's a valid Coteab theme JSON.");
                                    }
                                };
                                reader.readAsText(file);
                            };
                            input.click();
                        }}
                        style={{ flex: 1, height: "40px", fontSize: "14px", fontWeight: "bold", background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                    >
                        Import Theme File
                    </button>
                    <button 
                        className="btn" 
                        onClick={() => {
                            if (window.confirm("Are you sure you want to reset everything to default? All your custom CSS and theme changes will be lost!")) {
                                setThemeName("My Custom Theme");
                                setBgRoot("#09090b");
                                setAccentColor("#7c5bf5");
                                setBorderColor("#1f1f2e");
                                setSidebarHex("#0f0f14"); setSidebarAlpha(1);
                                setMainHex("#0d0d11"); setMainAlpha(1);
                                setCardHex("#15151e"); setCardAlpha(0.3);
                                setTextPrimary("#e4e4e7");
                                setTextSecondary("#a1a1aa");
                                setBgInput("#111119");
                                setBorderRadiusStr("0px");
                                setSuccessColor("#22c55e");
                                setDangerColor("#ef4444");
                                setWarningColor("#f59e0b");
                                setCornerColor("#7c5bf5");
                                setSidebarBorderWidth("1px");
                                setBgType("solid");
                                setCustomBgUrl("");
                                setGrad1("#7c5bf5"); setGrad2("#ff007f"); setGrad3("#00d2ff");
                                setCustomLabels({});
                                setCustomIcons({});
                                setCustomTitle("");
                                setCustomVersion("");
                                setFontUrl("");
                                setCustomCss("");
                            }
                        }}
                        style={{ flex: 1, height: "40px", fontSize: "14px", fontWeight: "bold", background: "#e74c3c", border: "1px solid var(--border)", color: "#fff" }}
                    >
                        Reset to Default
                    </button>
                </div>
            </div>
        </div>
    );
}
