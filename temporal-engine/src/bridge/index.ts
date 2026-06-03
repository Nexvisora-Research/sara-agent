export { TemporalEngineBridge } from "./rpc";

/**
 * Standalone entry point for the temporal engine.
 * Run as: node dist/bridge/standalone.js
 */
export async function runStandalone(): Promise<void> {
  const { TemporalEngineBridge } = await import("./rpc");
  const bridge = new TemporalEngineBridge();
  bridge.start();

  process.on("SIGINT", () => {
    bridge.stop();
    process.exit(0);
  });
  process.on("SIGTERM", () => {
    bridge.stop();
    process.exit(0);
  });
}

// Allow running as a standalone process
const isMainModule = process.argv.length >= 2 &&
  process.argv[1]?.endsWith("bridge/index.js") ||
  process.argv[1]?.endsWith("bridge/index.ts");
if (isMainModule) {
  runStandalone();
}
