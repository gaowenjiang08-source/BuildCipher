import { useEffect, useRef, useState } from "react";

export default function useDeferredMount({ rootMargin = "320px 0px", initiallyMounted = false } = {}) {
  const [mounted, setMounted] = useState(Boolean(initiallyMounted));
  const targetRef = useRef(null);

  useEffect(() => {
    if (mounted) return undefined;
    if (typeof window === "undefined") {
      setMounted(true);
      return undefined;
    }

    if (!("IntersectionObserver" in window)) {
      setMounted(true);
      return undefined;
    }

    const observer = new window.IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setMounted(true);
          observer.disconnect();
        }
      },
      { root: null, rootMargin, threshold: 0.01 }
    );

    const currentTarget = targetRef.current;
    if (currentTarget) {
      observer.observe(currentTarget);
    }

    return () => {
      observer.disconnect();
    };
  }, [mounted, rootMargin]);

  return {
    mounted,
    targetRef,
  };
}
