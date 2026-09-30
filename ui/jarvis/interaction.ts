export type WakeSource = "audio:clap_pattern" | "voice" | "manual";
export interface JarvisSession { readonly sessionId: string; readonly wakeSource: WakeSource; readonly active: boolean; }
export interface JarvisCommand { readonly sessionId: string; readonly text: string; readonly metadata: Record<string, unknown>; }

export function commandForActiveSession(session: JarvisSession, text: string): JarvisCommand {
  if (!session.active) throw new Error("jarvis_session_inactive");
  if (!text.trim()) throw new Error("input_text_required");
  return { sessionId: session.sessionId, text: text.trim(), metadata: { wakeSource: session.wakeSource } };
}
