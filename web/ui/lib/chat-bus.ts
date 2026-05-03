// Tiny module-level event bus so any UI surface (dashboard buttons,
// suggestion chips, future widgets) can dispatch a message into the chat
// panel without prop drilling or React context.

type Listener = (text: string) => void;

const listeners = new Set<Listener>();

export function emitChatMessage(text: string) {
  for (const l of listeners) l(text);
}

export function onChatMessage(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
