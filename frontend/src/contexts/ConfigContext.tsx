import { createContext, useContext, useState, useEffect, useCallback } from "react";
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

interface ConfigContextType {
    config: AppConfig | null;
    setConfig: (config: AppConfig) => void;
    saveConfig: (newConfig: AppConfig) => Promise<void>;
    isLoading: boolean;
    error: string | null;
    // Session Timer & Macro State
    isMacroRunning: boolean;
    setMacroRunning: (running: boolean) => void;
    sessionDuration: number; // Accumulated ms
    lastStartTime: number | null; // Start time of current run
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: ReactNode }) {
    const [config, setConfig] = useState<AppConfig | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Macro State
    const [isMacroRunning, setIsMacroRunningState] = useState(false);
    const [sessionDuration, setSessionDuration] = useState(0);
    const [lastStartTime, setLastStartTime] = useState<number | null>(null);

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

        return () => {
            delete (window as any).onConfigUpdated;
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
            setIsLoading(false);
        } catch (err) {
            console.error("Failed to load config:", err);
            setError(String(err));
            setIsLoading(false);
        }
    };

    const saveConfig = async (newConfig: AppConfig) => {
        try {
            setConfig(newConfig); // Optimistic update
            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.save_config(newConfig);
            }
            console.log("Config saved successfully");
        } catch (err) {
            console.error("Failed to save config:", err);
            setError(String(err));
        }
    };

    return (
        <ConfigContext.Provider value={{
            config, setConfig, saveConfig, isLoading, error,
            isMacroRunning, setMacroRunning, sessionDuration, lastStartTime
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
