import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

type SaraBackendResult = {
  ok: boolean;
  status?: string;
  reply: string;
  action_summaries?: string[];
  error?: string;
};

type AskSaraOptions = {
  userId?: string;
  channel?: string;
};

function findRepoRoot(): string {
  // dist/src/main -> Gui/dist/src/main at runtime
  return path.resolve(__dirname, '../../../..');
}

function resolvePythonExecutable(repoRoot: string): string {
  const envBin = process.env.SARA_PYTHON_BIN;
  if (envBin && envBin.trim()) return envBin;

  const candidates = [
    path.join(repoRoot, 'venv', 'bin', 'python'),
    path.join(repoRoot, '.venv', 'bin', 'python'),
    'python3',
    'python',
  ];

  for (const candidate of candidates) {
    if (candidate === 'python3' || candidate === 'python') return candidate;
    if (fs.existsSync(candidate)) return candidate;
  }

  return 'python3';
}

export async function askSara(message: string, options: AskSaraOptions = {}): Promise<SaraBackendResult> {
  const repoRoot = findRepoRoot();
  const pythonBin = resolvePythonExecutable(repoRoot);
  const bridgeScript = path.join(repoRoot, 'tools', 'gui_agent_bridge.py');

  if (!fs.existsSync(bridgeScript)) {
    return {
      ok: false,
      error: 'bridge_missing',
      reply: 'Sara backend bridge script is missing.',
    };
  }

  const payload = JSON.stringify({
    user_id: options.userId || 'gui_user',
    message,
    channel: options.channel || 'gui',
  });

  return new Promise((resolve) => {
    const child = spawn(pythonBin, [bridgeScript, payload], {
      cwd: repoRoot,
      env: process.env,
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += String(chunk);
    });

    child.stderr.on('data', (chunk) => {
      stderr += String(chunk);
    });

    child.on('error', (err) => {
      resolve({
        ok: false,
        error: String(err),
        reply: 'Failed to launch Sara backend process.',
      });
    });

    child.on('close', () => {
      const out = stdout.trim();
      if (!out) {
        resolve({
          ok: false,
          error: stderr.trim() || 'empty_response',
          reply: 'Sara backend returned an empty response.',
        });
        return;
      }

      try {
        const parsed = JSON.parse(extractJsonPayload(out)) as SaraBackendResult;
        resolve(parsed);
      } catch {
        resolve({
          ok: false,
          error: stderr.trim() || 'invalid_json',
          reply: out,
        });
      }
    });
  });
}

function extractJsonPayload(stdout: string): string {
  const lines = stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const jsonLine = [...lines].reverse().find((line) => line.startsWith('{') && line.endsWith('}'));
  return jsonLine || stdout;
}
