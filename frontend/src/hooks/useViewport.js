import { useEffect, useState } from "react";

export default function useViewport() {
  const [width, setWidth] = useState(() => {
    if (typeof window === "undefined") return 1280;
    return window.innerWidth;
  });

  useEffect(() => {
    function onResize() {
      setWidth(window.innerWidth);
    }

    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return {
    width,
    isMobile: width <= 900,
    isSmallMobile: width <= 480,
  };
}
