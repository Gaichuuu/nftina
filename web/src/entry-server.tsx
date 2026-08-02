import { StrictMode } from "react";
import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router";
import AppRoutes from "./routes";

export { compactUsd, compactUsdDown } from "./lib/format";

export function render(url: string): string {
  return renderToString(
    <StrictMode>
      <StaticRouter location={url}>
        <AppRoutes />
      </StaticRouter>
    </StrictMode>,
  );
}
