import { render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import ModelViewer, { skipForConnection } from "./ModelViewer";

it("prerenders a model-viewer tag with src + poster without throwing", () => {
  const html = renderToString(
    <ModelViewer src="https://cdn/mothman.gltf" poster="https://cdn/mothman.png" alt="Mothman" />);
  expect(html).toContain("model-viewer");
  expect(html).toContain("https://cdn/mothman.gltf");
  expect(html).toContain("autoplay");
});

it("omits autoplay when disabled", () => {
  const html = renderToString(<ModelViewer src="https://cdn/x.gltf" autoplay={false} />);
  expect(html).not.toContain("autoplay");
});

it("shows a loading spinner until the model's load event fires", () => {
  const html = renderToString(<ModelViewer src="https://cdn/x.glb" />);
  expect(html).toContain('aria-label="Loading 3D model"');
  expect(html).toContain("animate-spin");
});

describe("skipForConnection", () => {
  it("has no opinion when the browser reports nothing", () => {
    expect(skipForConnection(undefined)).toBe(false);
    expect(skipForConnection({})).toBe(false);
  });

  it("skips when the user asked to save data, or the connection is 2g", () => {
    expect(skipForConnection({ saveData: true })).toBe(true);
    expect(skipForConnection({ effectiveType: "2g" })).toBe(true);
    expect(skipForConnection({ effectiveType: "slow-2g" })).toBe(true);
  });

  it("loads normally on a usable connection", () => {
    expect(skipForConnection({ saveData: false, effectiveType: "4g" })).toBe(false);
    expect(skipForConnection({ effectiveType: "3g" })).toBe(false);
  });
});

describe("on a save-data connection", () => {
  const setConnection = (value: unknown) =>
    Object.defineProperty(navigator, "connection", { value, configurable: true });
  afterEach(() => setConnection(undefined));

  it("keeps the poster and never pulls the viewer", () => {
    setConnection({ saveData: true });
    render(<ModelViewer src="https://cdn/x.glb" poster="https://cdn/x.webp" alt="Mothman" />);
    expect(screen.getByAltText("Mothman")).toHaveAttribute("src", "https://cdn/x.webp");
    expect(screen.queryByLabelText("Loading 3D model")).toBeNull();
  });

  it("still renders the model when there is no poster to fall back to", () => {
    setConnection({ saveData: true });
    const { container } = render(<ModelViewer src="https://cdn/x.glb" />);
    expect(container.querySelector("model-viewer")).not.toBeNull();
  });
});
