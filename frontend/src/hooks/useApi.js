import { useEffect, useRef, useState } from 'react';

/**
 * Runs `request(signal)` whenever `deps` change. Stale responses are aborted,
 * and the previous data stays on screen while the next request is in flight.
 */
export function useApi(request, deps, { delay = 0 } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const requestRef = useRef(request);
  requestRef.current = request;

  useEffect(() => {
    const controller = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    const timer = setTimeout(() => {
      requestRef
        .current(controller.signal)
        .then((data) => setState({ data, error: null, loading: false }))
        .catch((error) => {
          if (error.name !== 'AbortError') setState((s) => ({ ...s, error, loading: false }));
        });
    }, delay);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, deps);

  return state;
}
