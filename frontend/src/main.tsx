import React from "react";
import ReactDOM from "react-dom/client";
import "./fonts.css";
import App from "./App";
import { ConfigProvider } from "./contexts/ConfigContext";


document.addEventListener('contextmenu', event => event.preventDefault());

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ConfigProvider>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
