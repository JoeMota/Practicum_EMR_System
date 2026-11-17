import { useEffect, useState, type DependencyList } from "react";

export function useAsync<T>(fn: () => Promise<T>, deps: DependencyList) {
  const [data, setData] = useState<T | undefined>();
  const [error, setError] = useState<Error | undefined>();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const depsKey = JSON.stringify(deps);

  useEffect(() => {
    let alive = true;
    fn()
      .then((d) => {
        if (alive) { setData(d); setError(undefined); }
      })
      .catch((e: Error) => { if (alive) setError(e); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
    // depsKey is the caller's dependency list. fn is recreated every render, so it stays out of the list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [depsKey, tick]);

  return { data, error, loading, reload: () => setTick((t) => t + 1), setData };
}
