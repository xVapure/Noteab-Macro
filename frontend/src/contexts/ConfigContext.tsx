import { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import type { ReactNode } from "react";
// Remove tauri invoke

export interface AppConfig {
    webhook_url: string[];
    private_server_link: string;
    roblox_username?: string;
    biome_notifier: Record<string, string>;
    biome_counts: Record<string, number>;
    merchant_counts?: Record<string, number>;
    enable_glitch_effect?: boolean;
    custom_biome_overrides?: Record<string, { color: string; thumbnail_url: string }>;
    [key: string]: any;
}

export type BiomeColorMap = Record<string, string>;

interface ConfigContextType {
    config: AppConfig | null;
    setConfig: (config: AppConfig) => void;
    saveConfig: (newConfig: AppConfig) => Promise<void>;
    saveConfigPatch: (key: string, value: any) => Promise<void>;
    isLoading: boolean;
    error: string | null;
    // Session Timer & Macro State
    isMacroRunning: boolean;
    setMacroRunning: (running: boolean) => void;
    sessionDuration: number; // Accumulated ms
    lastStartTime: number | null; // Start time of current run
    biomeColors: BiomeColorMap;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: ReactNode }) {
    const [config, setConfigState] = useState<AppConfig | null>(null);
    const configRef = useRef<AppConfig | null>(null);
    const saveQueueRef = useRef<Promise<void>>(Promise.resolve());
    const readyRef = useRef(false);
    const setConfig = useCallback((next: AppConfig) => {
        configRef.current = next;
        setConfigState(next);
    }, []);

    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Macro State
    const [isMacroRunning, setIsMacroRunningState] = useState(false);
    const [sessionDuration, setSessionDuration] = useState(0);
    const [lastStartTime, setLastStartTime] = useState<number | null>(null);
    const [biomeColors, setBiomeColors] = useState<BiomeColorMap>({});

    const setMacroRunning = useCallback((running: boolean) => {
        setIsMacroRunningState(running);
        if (running) {
            setLastStartTime(Date.now());
        } else {
            if (lastStartTime) {
                setSessionDuration(prev => prev + (Date.now() - lastStartTime));
            }
            setLastStartTime(null);
        }
    }, [lastStartTime]);

    useEffect(() => {
        // Wait for pywebview to be ready if it's not yet
        const initConfig = () => {
            if (window.pywebview && window.pywebview.api) {
                loadConfig();
            } else {
                window.addEventListener('pywebviewready', () => {
                    loadConfig();
                });
            }
        };
        initConfig();

        // Setup listener for Python to trigger frontend updates
        // In PyWebView, Python can call JS functions directly.
        // We expose a global function for Python to call when config updates.
        (window as any).onConfigUpdated = () => {
            console.log("Config updated remotely, reloading...");
            loadConfig();
        };

        (window as any).onStatsUpdated = async () => {
            try {
                if (window.pywebview?.api?.get_stats) {
                    const stats = await window.pywebview.api.get_stats();
                    if (configRef.current) {
                        setConfig({ ...configRef.current, ...stats });
                    }
                    if (stats.session_time) {
                        const parts = stats.session_time.split(":");
                        if (parts.length === 3) {
                            const h = parseInt(parts[0], 10) || 0;
                            const m = parseInt(parts[1], 10) || 0;
                            const s = parseInt(parts[2], 10) || 0;
                            setSessionDuration((h * 3600 + m * 60 + s) * 1000);
                            setLastStartTime(Date.now());
                        }
                    }
                }
            } catch (e) {
                console.warn("Stats update failed:", e);
            }
        };

        return () => {
            delete (window as any).onConfigUpdated;
            delete (window as any).onStatsUpdated;
        };
    }, []);

    const loadConfig = async () => {
        try {
            console.log("Loading config...");
            if (!window.pywebview || !window.pywebview.api || typeof window.pywebview.api.get_config !== 'function') {
                console.warn("Pywebview API not available yet, mock or wait.");
                setTimeout(loadConfig, 100);
                return;
            }
            const data = await window.pywebview.api.get_config();
            console.log("Config loaded:", data);

            if (data.session_time) {
                const parts = data.session_time.split(":");
                if (parts.length === 3) {
                    const hours = parseInt(parts[0], 10) || 0;
                    const mins = parseInt(parts[1], 10) || 0;
                    const secs = parseInt(parts[2], 10) || 0;
                    const ms = (hours * 3600 + mins * 60 + secs) * 1000;
                    setSessionDuration(ms);
                    setLastStartTime(Date.now()); // Reset tick offset so it stays perfectly synced
                }
            }

            setConfig(data);
            readyRef.current = true;
            setIsLoading(false);

            // Fetch biome colors from the tracker's GitHub-fetched biome_data
            try {
                if (window.pywebview?.api?.get_biome_data) {
                    const colors = await window.pywebview.api.get_biome_data();
                    if (colors && typeof colors === 'object') {
                        setBiomeColors(colors);
                    }
                }
            } catch (e) {
                console.warn("Could not fetch biome_data colors:", e);
            }
        } catch (err) {
            console.error("Failed to load config:", err);
            setError(String(err));
            setIsLoading(false);
        }
    };

    const saveConfig = async (newConfig: AppConfig) => {
        configRef.current = newConfig;
        setConfig(newConfig);
        if (!readyRef.current) return;
        const request = saveQueueRef.current.then(async () => {
            if (window.pywebview?.api) {
                await window.pywebview.api.save_config(newConfig);
            }
        });
        saveQueueRef.current = request.then(() => undefined, () => undefined);
        try {
            await request;
        } catch (err) {
            console.error("Failed to save config:", err);
            setError(String(err));
        }
    };

    const saveConfigPatch = async (key: string, value: any) => {
        const current = configRef.current;
        if (!current || !readyRef.current) return;
        const next = { ...current, [key]: value };
        configRef.current = next;
        setConfig(next);
        const request = saveQueueRef.current.then(async () => {
            if (window.pywebview?.api?.save_config_patch) {
                await window.pywebview.api.save_config_patch(key, value);
            } else if (window.pywebview?.api) {
                await window.pywebview.api.save_config(next);
            }
        });
        saveQueueRef.current = request.then(() => undefined, () => undefined);
        try {
            await request;
        } catch (err) {
            console.error("Failed to save config:", err);
            setError(String(err));
        }
    };
    return (
        <ConfigContext.Provider value={{
            config, setConfig, saveConfig, saveConfigPatch, isLoading, error,
            isMacroRunning, setMacroRunning, sessionDuration, lastStartTime,
            biomeColors
        }}>
            {children}
        </ConfigContext.Provider>
    );
}

export function useConfig() {
    const context = useContext(ConfigContext);
    if (context === undefined) {
        throw new Error("useConfig must be used within a ConfigProvider");
    }
    return context;
}
