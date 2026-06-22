import { useEffect, useState } from "react";

export function useGpuTier(): number {
  const [tier, setTier] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined" || !window.WebGLRenderingContext) {
      setTier(0);
      return;
    }

    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");

    if (!gl) {
      setTier(0);
      return;
    }

    const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
    if (!debugInfo) {
      setTier(1);
      return;
    }

    const renderer = (
      gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) ?? ""
    ).toLowerCase();
    const vendor = (
      gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) ?? ""
    ).toLowerCase();

    if (
      renderer.includes("swiftshader") ||
      renderer.includes("llvmpipe") ||
      renderer.includes("mesa")
    ) {
      setTier(0);
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mediaQuery.matches) {
      setTier(0);
      return;
    }

    const isMobile = /android|iphone|ipad/i.test(navigator.userAgent);
    if (isMobile) {
      setTier(1);
      return;
    }

    const isIntegrated =
      vendor.includes("intel") || renderer.includes("intel");
    setTier(isIntegrated ? 2 : 3);
  }, []);

  return tier;
}
