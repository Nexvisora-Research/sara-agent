import type { ScheduledJob, WorkerStatus, TemporalEvent } from "../types";

export class BackgroundWorker {
  private jobs: Map<string, ScheduledJob> = new Map();
  private timers: Map<string, ReturnType<typeof setInterval>> = new Map();
  private status: WorkerStatus = "idle";
  private tickIntervalMs: number;
  private tickTimer: ReturnType<typeof setInterval> | null = null;
  private listeners: Map<string, Set<(event: TemporalEvent) => void>> = new Map();
  private onTick: ((jobs: ScheduledJob[]) => Promise<void>) | null = null;

  constructor(opts?: { tickIntervalMs?: number }) {
    this.tickIntervalMs = opts?.tickIntervalMs ?? 60_000;
  }

  // ─── Job Management ───────────────────────────────────────────────

  addJob(job: ScheduledJob): void {
    this.jobs.set(job.id, { ...job });
    this._scheduleJob(job);
    this._emit("job:triggered", job);
  }

  removeJob(id: string): boolean {
    const existed = this.jobs.has(id);
    this.jobs.delete(id);
    this._clearTimer(id);
    return existed;
  }

  getJob(id: string): ScheduledJob | undefined {
    return this.jobs.get(id);
  }

  listJobs(): ScheduledJob[] {
    return Array.from(this.jobs.values());
  }

  pauseJob(id: string): boolean {
    const job = this.jobs.get(id);
    if (!job) return false;
    job.status = "paused";
    this._clearTimer(id);
    return true;
  }

  resumeJob(id: string): boolean {
    const job = this.jobs.get(id);
    if (!job) return false;
    job.status = "active";
    this._scheduleJob(job);
    return true;
  }

  // ─── Lifecycle ────────────────────────────────────────────────────

  start(): void {
    if (this.status === "running") return;
    this.status = "running";

    this.tickTimer = setInterval(() => {
      this._tick();
    }, this.tickIntervalMs);

    // Reschedule all active jobs
    for (const job of this.jobs.values()) {
      if (job.status === "active") this._scheduleJob(job);
    }
  }

  stop(): void {
    this.status = "idle";
    if (this.tickTimer) clearInterval(this.tickTimer);
    this.tickTimer = null;
    for (const [id] of this.timers) this._clearTimer(id);
  }

  pause(): void {
    this.status = "paused";
    if (this.tickTimer) clearInterval(this.tickTimer);
    this.tickTimer = null;
  }

  getStatus(): WorkerStatus {
    return this.status;
  }

  // ─── Event Bus ────────────────────────────────────────────────────

  on(eventType: string, cb: (event: TemporalEvent) => void): () => void {
    if (!this.listeners.has(eventType)) this.listeners.set(eventType, new Set());
    this.listeners.get(eventType)!.add(cb);
    return () => this.listeners.get(eventType)?.delete(cb);
  }

  setTickHandler(handler: (jobs: ScheduledJob[]) => Promise<void>): void {
    this.onTick = handler;
  }

  // ─── Cron Parsing ─────────────────────────────────────────────────

  getNextRun(cronExpression: string, after = Date.now()): number {
    const parts = cronExpression.trim().split(/\s+/);
    if (parts.length < 5) return after + this.tickIntervalMs;

    const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;
    const next = new Date(after);
    next.setSeconds(0, 0);

    const minuteNum = this._parseCronField(minute, 0, 59);
    const hourNum = this._parseCronField(hour, 0, 23);
    const domNum = this._parseCronField(dayOfMonth, 1, 31);
    const monthNum = this._parseCronField(month, 1, 12);
    const dowNum = this._parseCronField(dayOfWeek, 0, 6);

    // If after rounding down, we're at or before base, advance one minute
    if (next.getTime() <= after) {
      next.setMinutes(next.getMinutes() + 1, 0, 0);
    }

    const maxIterations = 525_600; // 1 year of minutes
    for (let i = 0; i < maxIterations; i++) {
      if (!this._matchesField(next.getMonth() + 1, monthNum)) { next.setMonth(next.getMonth() + 1); next.setDate(1); next.setHours(0, 0, 0, 0); continue; }
      if (!this._matchesField(next.getDate(), domNum)) { next.setDate(next.getDate() + 1); next.setHours(0, 0, 0, 0); continue; }
      if (!this._matchesField(next.getDay(), dowNum)) { next.setDate(next.getDate() + 1); next.setHours(0, 0, 0, 0); continue; }
      if (!this._matchesField(next.getHours(), hourNum)) { next.setHours(next.getHours() + 1, 0, 0, 0); continue; }
      if (!this._matchesField(next.getMinutes(), minuteNum)) { next.setMinutes(next.getMinutes() + 1, 0, 0); continue; }
      return next.getTime();
    }
    return after + this.tickIntervalMs;
  }

  private _parseCronField(field: string, min: number, max: number): number[] {
    if (field === "*") return Array.from({ length: max - min + 1 }, (_, i) => i + min);
    const values: number[] = [];
    for (const part of field.split(",")) {
      if (part.includes("/")) {
        const [range, step] = part.split("/");
        const [rMin, rMax] = range === "*" ? [min, max] : range.split("-").map(Number);
        for (let v = rMin; v <= (rMax ?? max); v += Number(step)) values.push(v);
      } else if (part.includes("-")) {
        const [s, e] = part.split("-").map(Number);
        for (let v = s; v <= e; v++) values.push(v);
      } else {
        values.push(Number(part));
      }
    }
    return values.filter((v) => v >= min && v <= max);
  }

  private _matchesField(value: number, allowed: number[]): boolean {
    return allowed.length === 0 || allowed.includes(value);
  }

  // ─── Internal ─────────────────────────────────────────────────────

  private _scheduleJob(job: ScheduledJob): void {
    this._clearTimer(job.id);
    const nextRun = this.getNextRun(job.cronExpression, job.nextRunAt);

    const delay = Math.max(0, nextRun - Date.now());
    const timer = setTimeout(() => {
      this._executeJob(job);
    }, delay);

    this.timers.set(job.id, timer);
    job.nextRunAt = nextRun;
  }

  private async _executeJob(job: ScheduledJob): Promise<void> {
    this._emit("job:triggered", job);
    try {
      if (this.onTick) await this.onTick([job]);
      job.lastRunAt = Date.now();
      job.status = "active";
      this._scheduleJob(job);
      this._emit("job:completed", job);
    } catch {
      job.retryCount++;
      job.status = job.retryCount >= job.maxRetries ? "failed" : "active";
      this._emit("job:failed", job);
      if (job.status === "active") this._scheduleJob(job);
    }
  }

  private _tick(): void {
    const active = this.listJobs().filter((j) => j.status === "active");
    for (const job of active) {
      if (Date.now() >= job.nextRunAt) {
        this._clearTimer(job.id);
        this._executeJob(job);
      }
    }
    this._emit("worker:tick", { jobs: active.length });
  }

  private _clearTimer(id: string): void {
    const t = this.timers.get(id);
    if (t) clearTimeout(t);
    this.timers.delete(id);
  }

  private _emit(type: string, payload: unknown): void {
    const event: TemporalEvent = { type: type as TemporalEvent["type"], timestamp: Date.now(), payload };
    const handlers = this.listeners.get(type);
    if (handlers) for (const cb of handlers) cb(event);
  }
}
