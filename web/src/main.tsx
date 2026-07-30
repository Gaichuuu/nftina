import { StrictMode } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
const root = document.getElementById("root")!;
if (root.hasChildNodes()) {
  hydrateRoot(
    root,
    <StrictMode>
      <App />
    </StrictMode>,
  );
} else {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
