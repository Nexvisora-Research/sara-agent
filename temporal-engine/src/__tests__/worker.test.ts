import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { BackgroundWorker } from "../scheduler/worker";

describe("BackgroundWorker", () => {
  let worker: BackgroundWorker;

  beforeEach(() => {
    vi.useFakeTimers();
    worker = new BackgroundWorker({ tickIntervalMs: 1000 });
  });

  afterEach(() => {
    worker.stop();
    vi.useRealTimers();
  });

  it("starts and stops", () => {
    expect(worker.getStatus()).toBe("idle");
    worker.start();
    expect(worker.getStatus()).toBe("running");
    worker.stop();
    expect(worker.getStatus()).toBe("idle");
  });

  it("pauses and resumes", () => {
    worker.start();
    worker.pause();
    expect(worker.getStatus()).toBe("paused");
    worker.resumeJob("nonexistent"); // no-op, just checking resume path
  });

  it("manages jobs", () => {
    worker.addJob({
      id: "j1",
      name: "Test Job",
      cronExpression: "0 9 * * *",
      action: { type: "reanalyze" as const, scope: "habits" as const },
      status: "active",
      nextRunAt: Date.now() + 86400000,
      retryCount: 0,
      maxRetries: 3,
      metadata: {},
    });

    expect(worker.listJobs()).toHaveLength(1);
    expect(worker.getJob("j1")?.name).toBe("Test Job");

    worker.pauseJob("j1");
    const paused = worker.getJob("j1");
    expect(paused?.status).toBe("paused");

    worker.resumeJob("j1");
    expect(worker.getJob("j1")?.status).toBe("active");

    worker.removeJob("j1");
    expect(worker.listJobs()).toHaveLength(0);
  });

  it("parses cron expressions for next run", () => {
    const base = new Date("2026-01-05T00:00:00Z").getTime(); // Monday
    const next = worker.getNextRun("30 9 * * 1-5", base);
    const d = new Date(next);
    expect(d.getHours()).toBe(9);
    expect(d.getMinutes()).toBe(30);
    expect([1, 2, 3, 4, 5]).toContain(d.getDay());
  });

  it("parses wildcard cron", () => {
    const base = Date.now();
    const next = worker.getNextRun("* * * * *", base);
    expect(next).toBeGreaterThanOrEqual(base);
  });

  it("fires events when jobs trigger", async () => {
    const events: string[] = [];
    worker.on("job:triggered", (e) => events.push(e.type));

    worker.addJob({
      id: "event-test",
      name: "Event Test",
      cronExpression: "* * * * *",
      action: { type: "reanalyze", scope: "all" },
      status: "active",
      nextRunAt: Date.now() - 1000,
      retryCount: 0,
      maxRetries: 3,
      metadata: {},
    });

    // Tick should trigger the job
    vi.advanceTimersByTime(2000);
    expect(events.length).toBeGreaterThanOrEqual(1);
  });
});
