import { useEffect, useState } from "react";

function resolveActiveSection(sectionIds = []) {
  if (typeof window === "undefined") return sectionIds[0] || "";

  const OFFSET_TOP = 150;
  const sections = sectionIds
    .map((id) => {
      const element = document.getElementById(id);
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      return {
        id,
        top: rect.top,
        bottom: rect.bottom,
      };
    })
    .filter(Boolean);

  if (sections.length === 0) return "";

  const inViewport = sections.filter((item) => item.top <= OFFSET_TOP && item.bottom >= OFFSET_TOP);
  if (inViewport.length > 0) {
    return inViewport.sort((a, b) => Math.abs(a.top - OFFSET_TOP) - Math.abs(b.top - OFFSET_TOP))[0]?.id || "";
  }

  const belowTop = sections.filter((item) => item.top > OFFSET_TOP).sort((a, b) => a.top - b.top);
  if (belowTop.length > 0) {
    return belowTop[0]?.id || "";
  }

  return sections.sort((a, b) => b.top - a.top)[0]?.id || "";
}

export default function useSectionSpy(sectionIds = []) {
  const [activeSectionId, setActiveSectionId] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    let frameId = 0;
    const evaluate = () => {
      const nextId = resolveActiveSection(sectionIds);
      setActiveSectionId((prev) => (prev === nextId ? prev : nextId));
    };
    const scheduleEvaluate = () => {
      if (frameId) window.cancelAnimationFrame(frameId);
      frameId = window.requestAnimationFrame(evaluate);
    };

    scheduleEvaluate();
    window.addEventListener("scroll", scheduleEvaluate, { passive: true });
    window.addEventListener("resize", scheduleEvaluate);

    return () => {
      if (frameId) window.cancelAnimationFrame(frameId);
      window.removeEventListener("scroll", scheduleEvaluate);
      window.removeEventListener("resize", scheduleEvaluate);
    };
  }, [sectionIds]);

  return activeSectionId;
}
