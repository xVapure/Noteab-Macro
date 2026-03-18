import React from "react";

interface ToggleSwitchProps {
    label: string;
    description?: React.ReactNode;
    checked: boolean;
    onChange: (val: boolean) => void;
}

export default function ToggleSwitch({ label, description, checked, onChange }: ToggleSwitchProps) {
    return (
        <div className="toggle-row">
            <div className="toggle-label">
                <span className="label-text">{label}</span>
                {description && <span className="label-desc">{description}</span>}
            </div>
            <label className="toggle-switch">
                <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
                <span className="toggle-slider" />
            </label>
        </div>
    );
}
