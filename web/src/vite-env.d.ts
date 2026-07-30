/// <reference types="vite/client" />

declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "model-viewer": React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        src?: string;
        poster?: string;
        alt?: string;
        "auto-rotate"?: boolean;
        "auto-rotate-delay"?: number;
        "rotation-per-second"?: string;
        "camera-controls"?: boolean;
        "camera-orbit"?: string;
        "interaction-prompt"?: string;
        "touch-action"?: string;
        "tone-mapping"?: string;
        exposure?: string;
        "shadow-intensity"?: string;
        "animation-name"?: string;
        autoplay?: boolean;
        ar?: boolean;
        loading?: string;
      };
    }
  }
}
export {}; 
