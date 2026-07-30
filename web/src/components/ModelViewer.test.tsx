import { renderToString } from "react-dom/server";
import ModelViewer from "./ModelViewer";

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
