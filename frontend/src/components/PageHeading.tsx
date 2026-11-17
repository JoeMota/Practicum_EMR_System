import { useMemo, useState, type ReactNode } from "react";
import { PageHeadingContext, type Heading } from "./usePageHeading";

export function PageHeadingProvider({ children }: { children: ReactNode }) {
  const [heading, setHeading] = useState<Heading | null>(null);
  const value = useMemo(() => ({ heading, setHeading }), [heading]);
  return <PageHeadingContext.Provider value={value}>{children}</PageHeadingContext.Provider>;
}
