import { useState } from "react";
import "./UpdateBanner.css";

interface UpdateBannerProps {
    version: string;
    downloadUrl: string;
    updateStatus: string | null;
}

export default function UpdateBanner({ version, downloadUrl, updateStatus }: UpdateBannerProps) {
    const [isUpdatingLocal, setIsUpdatingLocal] = useState(false);

    const handleUpdate = async () => {
        setIsUpdatingLocal(true);
        try {
            if (window.pywebview && window.pywebview.api) {
                await window.pywebview.api.apply_update(downloadUrl, version);
            }
        } catch (e) {
            setIsUpdatingLocal(false);
        }
    };

    const failed = updateStatus === "failed";
    const isDone = updateStatus?.startsWith("done|") ?? false;
    const doneFilename = isDone ? updateStatus!.split("|")[1] : "";
    const isUpdating = isUpdatingLocal || updateStatus === "downloading";

    if ((failed || isDone) && isUpdatingLocal) {
        setIsUpdatingLocal(false);
    }

    return (
        <div className={`update-banner ${failed ? "update-banner-error" : ""} ${isDone ? "update-banner-success" : ""}`}>
            <div className="update-banner-content">
                <span className="update-icon">
                    {failed ? "⚠️" : isDone ? "✅" : "❗"}
                </span>
                <span className="update-text">
                    {failed
                        ? "Update failed. Please try downloading again."
                        : isDone
                            ? `Updated! ${doneFilename || "Restarting"}`
                            : isUpdating
                                ? "Downloading update..."
                                : `New Coteab Macro ${version} is available!!!`
                    }
                </span>
            </div>
            {!isUpdating && !isDone && (
                <div className="update-banner-actions">
                    <button className="update-btn update-btn-primary" onClick={handleUpdate}>
                        {failed ? "Retry Update" : "Update Now"}
                    </button>
                </div>
            )}
            {isUpdating && !failed && !isDone && (
                <div className="update-spinner" />
            )}
        </div>
    );
}
