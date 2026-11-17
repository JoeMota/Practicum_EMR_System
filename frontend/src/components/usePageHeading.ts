import { createContext, useContext, useEffect } from "react";

export interface Heading {
  title: string;
}

export interface HeadingCtx {
  heading: Heading | null;
  setHeading: (h: Heading | null) => void;
}

export const PageHeadingContext = createContext<HeadingCtx | null>(null);

export function usePageHeading(title: string) {
  const ctx = useContext(PageHeadingContext);
  const setHeading = ctx?.setHeading;
  useEffect(() => {
    if (!setHeading) return;
    setHeading({ title });
    return () => setHeading(null);
  }, [setHeading, title]);
}

export function usePageHeadingValue() {
  return useContext(PageHeadingContext)?.heading ?? null;
}
