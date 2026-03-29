import { createContext, useContext, useEffect, useMemo, useReducer } from "react";
import { fetchChamberStatus, normalizeChamberSnapshot } from "../api/client";
import { chamberReducer, initialChamberState } from "./chamberReducer";

const ChamberContext = createContext(null);

export function ChamberProvider({ children }) {
  const [state, dispatch] = useReducer(chamberReducer, initialChamberState);

  useEffect(() => {
    let cancelled = false;
    async function pull() {
      try {
        const raw = await fetchChamberStatus();
        if (cancelled) return;
        const n = normalizeChamberSnapshot(raw);
        if (n) dispatch({ type: "HYDRATE_CHAMBER", payload: { snapshot: n, mode: "status" } });
      } catch {
        /* backend may be down — UI keeps local state */
      }
    }
    void pull();
    const t = setInterval(pull, 2500);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  const value = useMemo(() => ({ state, dispatch }), [state, dispatch]);
  return (
    <ChamberContext.Provider value={value}>{children}</ChamberContext.Provider>
  );
}

export function useChamber() {
  const ctx = useContext(ChamberContext);
  if (!ctx) {
    throw new Error("useChamber must be used within ChamberProvider");
  }
  return ctx;
}
