import { useRef, useState } from "react";

export function useRing<T>(max = 120) {
  const buf = useRef<T[]>([]);
  const [, setTick] = useState(0); // trigger re-render

  const push = (v: T) => {
    buf.current.push(v);
    if (buf.current.length > max) buf.current.shift();
    setTick((n) => n + 1);
  };

  const clear = () => {
    buf.current = [];
    setTick((n) => n + 1);
  };

  return { data: buf.current, push, clear };
}
