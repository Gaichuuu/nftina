import { render } from "@testing-library/react";
import LoopMedia from "./LoopMedia";

it("plays the loop when there is one, with the still as poster", () => {
  const { container } = render(
    <LoopMedia image="https://cdn/still.jpg" video="https://cdn/loop.mp4" alt="Mothman" />);
  const v = container.querySelector("video")!;
  expect(v.getAttribute("src")).toBe("https://cdn/loop.mp4");
  expect(v.getAttribute("poster")).toBe("https://cdn/still.jpg");
  expect(v).toHaveAttribute("loop");
  expect(v).toHaveAttribute("playsinline");
  expect(container.querySelector("img")).toBeNull();
});

it("shows the still when there is no loop", () => {
  const { container } = render(<LoopMedia image="https://cdn/still.jpg" alt="Bigfoot" />);
  expect(container.querySelector("img")).toHaveAttribute("src", "https://cdn/still.jpg");
  expect(container.querySelector("video")).toBeNull();
});

it("renders nothing when there is neither, so the caller's placeholder shows", () => {
  const { container } = render(<LoopMedia alt="none" />);
  expect(container).toBeEmptyDOMElement();
});
