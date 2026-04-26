import { useState, useEffect, useRef } from "react";
import "./App.css";
import { useConfig } from "./contexts/ConfigContext";
import Sidebar from "./components/Sidebar";
import HeaderBar from "./components/HeaderBar";
import NoticePage from "./pages/NoticePage";
import WebhookPage from "./pages/WebhookPage";
import CalibrationPage from "./pages/CalibrationPage";
import MiscPage from "./pages/MiscPage";
import FishingPage from "./pages/FishingPage";
import MerchantPage from "./pages/MerchantPage";
import AutoPopBuffPage from "./pages/AutoPopBuffPage";
import AurasPage from "./pages/AurasPage";
import PotionCraftPage from "./pages/PotionCraftPage";
import StatsPage from "./pages/StatsPage";
import OtherFeaturesPage from "./pages/OtherFeaturesPage";
import CreditsPage from "./pages/CreditsPage";
import DonationsPage from "./pages/DonationsPage";
import RemoteAccessPage from "./pages/RemoteAccessPage";
import CalibrationOverlay from "./components/CalibrationOverlay";
import GlitchOverlay from "./components/GlitchOverlay";
import UpdateBanner from "./components/UpdateBanner";
import CustomizationPage from "./pages/CustomizationPage";
import MovementsPage from "./pages/MovementsPage";
import RecorderWindow from "./pages/RecorderWindow";
import BiomeConfirmWindow from "./pages/BiomeConfirmWindow";

const pages: Record<string, React.FC> = {
  notice: NoticePage,
  webhook: WebhookPage,
  calibrations: CalibrationPage,
  remoteaccess: RemoteAccessPage,
  misc: MiscPage,
  fishing: FishingPage,
  merchant: MerchantPage,
  autopopbuff: AutoPopBuffPage,
  auras: AurasPage,
  movements: MovementsPage,
  potioncraft: PotionCraftPage,
  stats: StatsPage,
  otherfeatures: OtherFeaturesPage,
  customization: CustomizationPage,
  credits: CreditsPage,
  donations: DonationsPage,
  // puzzle: PuzzlePage,
};

function App() {
  const [activeTab, setActiveTab] = useState("notice");
  const { config, saveConfig, isMacroRunning, setMacroRunning } = useConfig();
  const [theme, setTheme] = useState("midnight");
  const [isGlitching, setIsGlitching] = useState(false);
  const [macroVersion, setMacroVersion] = useState("v?.?.?");
  const [updateInfo, setUpdateInfo] = useState<{ version: string; url: string } | null>(null);
  const [updateStatus, setUpdateStatus] = useState<string | null>(null);
  const autoUpdateTriggerRef = useRef<string | null>(null);
  const startupUpdateCheckRequestedRef = useRef(false);
  const isAutoUpdateEnabled = config ? (config.auto_update_enabled !== false) : false;


  const startMacro = async () => {
    if (isMacroRunning) return;
    setMacroRunning(true);
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.set_biome_detection(true);
      }
    } catch (e) {
      console.error("Failed to start macro api:", e);
    }
  };

  const stopMacro = async () => {
    if (!isMacroRunning) return;
    setMacroRunning(false);
    try {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.set_biome_detection(false);
      }
    } catch (e) {
      console.error("Failed to stop macro api:", e);
    }
  };

  const toggleMacro = () => {
    if (isMacroRunning) stopMacro();
    else startMacro();
  };

  // track running state inside event callbacks
  const isRunningRef = useRef(isMacroRunning);
  const processingRef = useRef(false);

  useEffect(() => {
    isRunningRef.current = isMacroRunning;
  }, [isMacroRunning]);

  useEffect(() => {
    const setupListeners = async () => {
      try {
        console.log("Setting up global listeners");

        (window as any).onShortcutEvent = async (key: string) => {
          if (processingRef.current) return;
          processingRef.current = true;

          try {
            if (key === "START") {
              if (!isRunningRef.current) {
                console.log("Start Shortcut (Backend) - Starting");
                setMacroRunning(true);
              }
            } else if (key === "STOP") {
              if (isRunningRef.current) {
                console.log("Stop Shortcut (Backend) - Stopping");
                setMacroRunning(false);
              }
            }
          } finally {
            setTimeout(() => {
              processingRef.current = false;
            }, 300);
          }
        };

        (window as any).onMacroStatus = (status: string) => {
          console.log("Macro Status Event:", status);
          if (status === "RUNNING" || status.includes("RUNNING")) {
            setMacroRunning(true);
          } else {
            setMacroRunning(false);
          }
        };

      } catch (err) {
        console.error("Failed to setup listeners:", err);
      }
    };

    setupListeners();

    // Clean up listener on unmount
    return () => {
      delete (window as any).onShortcutEvent;
      delete (window as any).onMacroStatus;
    };
  }, []);

  useEffect(() => {
    (window as any).onFishingFailsafeWarning = (message: string) => {
      if (message) {
        alert(message);
      }
      setActiveTab("misc");
    };

    return () => {
      delete (window as any).onFishingFailsafeWarning;
    };
  }, []);

  // Biome Listener
  useEffect(() => {
    const setupBiomeListener = async () => {
      (window as any).onBiomeUpdate = (payload: string) => {
        const biome = (payload || "").toUpperCase().trim();
        if ((biome === "GLITCHED") && config?.enable_glitch_effect) {
          setIsGlitching(true);
        } else {
          setIsGlitching(false);
        }
      };
    };

    setupBiomeListener();

    return () => {
      delete (window as any).onBiomeUpdate;
    };
  }, [config]);



  // Check Update Listener
  useEffect(() => {
    (window as any).onUpdateAvailable = (version: string, url: string) => {
      console.log("Update available:", version, url);
      setUpdateInfo({ version, url });
    };

    (window as any).onUpdateStatus = (status: string) => {
      console.log("Update status:", status);
      setUpdateStatus(status);
    };

    return () => {
      delete (window as any).onUpdateAvailable;
      delete (window as any).onUpdateStatus;
    };
  }, []);

  useEffect(() => {
    const shouldAutoUpdate = isAutoUpdateEnabled;
    if (!updateInfo || !shouldAutoUpdate) return;

    const updateKey = `${updateInfo.version}|${updateInfo.url}`;
    if (autoUpdateTriggerRef.current === updateKey) return;
    autoUpdateTriggerRef.current = updateKey;

    const applyAutoUpdate = async () => {
      try {
        setUpdateStatus("downloading");
        if (window.pywebview?.api?.apply_update) {
          await window.pywebview.api.apply_update(updateInfo.url, updateInfo.version);
        }
      } catch (err) {
        console.error("Auto update apply failed:", err);
        setUpdateStatus("failed");
        autoUpdateTriggerRef.current = null;
      }
    };

    void applyAutoUpdate();
  }, [updateInfo, isAutoUpdateEnabled]);

  useEffect(() => {
    if (!config) return;
    if (startupUpdateCheckRequestedRef.current) return;
    startupUpdateCheckRequestedRef.current = true;

    const requestUpdateCheck = async () => {
      try {
        if (config && (config as any).dont_ask_for_update) {
            return;
        }
        if (window.pywebview?.api?.get_update_available) {
          const info = await window.pywebview.api.get_update_available();
          if (info && info.version && info.url) {
            setUpdateInfo({ version: String(info.version), url: String(info.url) });
            return;
          }
        }

        if (window.pywebview?.api?.check_for_updates) {
          await window.pywebview.api.check_for_updates();
        }
      } catch (err) {
        console.error("Startup update check failed:", err);
        startupUpdateCheckRequestedRef.current = false;
      }
    };

    const onReady = () => {
      void requestUpdateCheck();
    };

    if (window.pywebview?.api) {
      void requestUpdateCheck();
      return;
    }

    window.addEventListener("pywebviewready", onReady, { once: true });
    return () => {
      window.removeEventListener("pywebviewready", onReady);
    };
  }, [config]);

  useEffect(() => {
    (window as any).onNavigateTab = (tabId: string) => {
      const normalized = String(tabId || "").trim().toLowerCase();
      if (normalized && pages[normalized]) {
        setActiveTab(normalized);
      }
    };
    return () => {
      delete (window as any).onNavigateTab;
    };
  }, []);

  // Load macro version from backend (single source in main.py)
  useEffect(() => {
    let cancelled = false;

    const applyVersion = (value: unknown) => {
      const version = String(value ?? "").trim();
      if (!version) return false;
      if (!cancelled) {
        setMacroVersion(version);
      }
      document.title = `Coteab Macro ${version}`;
      return true;
    };

    const loadMacroVersion = async (): Promise<boolean> => {
      try {
        if (window.pywebview?.api && typeof window.pywebview.api.get_macro_version === "function") {
          const version = await window.pywebview.api.get_macro_version();
          return applyVersion(version);
        }
      } catch (err) {
        console.error("Failed to load macro version:", err);
      }
      return false;
    };

    const tryLoad = async () => {
      for (let i = 0; i < 10 && !cancelled; i++) {
        if (await loadMacroVersion()) return;
        await new Promise(r => setTimeout(r, 500));
      }
    };

    void tryLoad();

    return () => {
      cancelled = true;
    };
  }, []);

  // Local Listener for when App is Focused
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "F1") {
        console.log("Frontend Listener: F1 Pressed");
        startMacro();
      } else if (e.key === "F2") {
        console.log("Frontend Listener: F2 Pressed");
        stopMacro();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isMacroRunning]);

  // Sync theme
  useEffect(() => {
    if (config && config.selected_theme) {
      setTheme(config.selected_theme);
    }
  }, [config]);

  // Apply theme
  useEffect(() => {
    document.body.setAttribute("data-theme", theme);
  }, [theme]);

  const handleThemeChange = (newTheme: string) => {
    setTheme(newTheme);
    if (config) {
      saveConfig({ ...config, selected_theme: newTheme });
    }
  };



  const activePageQuery = (window as any).__INJECTED_OVERLAY__ || new URLSearchParams(window.location.search).get("overlay");
  const windowType = (window as any).__INJECTED_WINDOW_TYPE__ || new URLSearchParams(window.location.search).get("window");

  if (windowType === "recorder") {
    return <RecorderWindow />;
  }

  if (windowType === "biome_confirm") {
    return <BiomeConfirmWindow />;
  }

  if (activePageQuery) {
    const mode = activePageQuery === "region" ? "region" : "point";
    return <CalibrationOverlay mode={mode} />;
  }

  const ActivePage = pages[activeTab] ?? NoticePage;

  return (

    <div className={`window-frame ${isGlitching ? 'is-glitching' : ''}`} style={{
      backgroundImage: config?.custom_background_image ? `url("file://${config.custom_background_image}")` : undefined,
      backgroundSize: "cover",
      backgroundPosition: "center",
      backgroundRepeat: "no-repeat"
    }}>
      <div className="corner-bracket tl" />
      <div className="corner-bracket tr" />
      <div className="corner-bracket bl" />
      <div className="corner-bracket br" />
      <div className="app-layout">
        <Sidebar activeTab={activeTab} onTabChange={setActiveTab} isGlitching={isGlitching} macroVersion={macroVersion} />
        <div className="main-content" style={{ position: "relative" }}>
          <HeaderBar
            isRunning={isMacroRunning}
            onToggle={toggleMacro}
            theme={theme}
            onThemeChange={handleThemeChange}
            isGlitching={isGlitching}
            setActiveTab={setActiveTab}
          />
          {updateInfo && (
            <UpdateBanner
              version={updateInfo.version}
              downloadUrl={updateInfo.url}
              updateStatus={updateStatus}
              onDismiss={() => setUpdateInfo(null)}
              onDontAskAgain={async () => {
                if (config) {
                  await saveConfig({ ...config, dont_ask_for_update: true });
                }
                setUpdateInfo(null);
              }}
            />
          )}
          <div className="page-content">
            <div className="fade-in" key={activeTab}>
              <ActivePage />
            </div>
          </div>
        </div>
      </div>
      {isGlitching && <GlitchOverlay />}


    </div>
  );
}

export default App;