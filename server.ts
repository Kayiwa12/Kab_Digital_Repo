import express from "express";
import { spawn, execSync, ChildProcess } from "child_process";
import { createProxyMiddleware } from "http-proxy-middleware";
import path from "path";
import http from "http";

const app = express();
const PORT = 3000;
const DJANGO_PORT = 8888;
const DJANGO_HOST = "127.0.0.1";

let djangoProcess: ChildProcess | null = null;
let isDjangoReady = false;
let isShuttingDown = false;

function ensurePythonEnvironment(): void {
  try {
    execSync("python3 -c 'import django, rest_framework, sklearn, whitenoise'", { stdio: "ignore" });
    console.log("[Proxy] Python environment and Django dependencies verified.");
  } catch {
    console.log("[Proxy] Python environment incomplete. Auto-installing required packages...");
    try {
      execSync("DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold' python3-pip python3-venv", { stdio: "inherit" });
      execSync("pip3 install -r requirements.txt --break-system-packages", { stdio: "inherit" });
      console.log("[Proxy] Python environment and packages installed successfully.");
    } catch (err: any) {
      console.error("[Proxy Error] Failed to auto-install Python dependencies:", err.message);
    }
  }
}

function startDjangoServer(): void {
  const pythonPath = "python3";
  console.log(`[Proxy] Starting Django server with command: ${pythonPath}`);

  djangoProcess = spawn(
    pythonPath,
    ["manage.py", "runserver", `${DJANGO_HOST}:${DJANGO_PORT}`, "--noreload"],
    {
      cwd: process.cwd(),
      stdio: "pipe",
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    }
  );

  djangoProcess.stdout?.on("data", (data) => {
    const text = data.toString();
    console.log(`[Django] ${text.trim()}`);
    if (text.includes("Starting development server") || text.includes("Quit the server with")) {
      isDjangoReady = true;
    }
  });

  djangoProcess.stderr?.on("data", (data) => {
    const text = data.toString().trim();
    // Django runserver writes standard HTTP access logs to stderr; distinguish normal logs from actual exceptions
    if (text.includes("HTTP/1.1\" 200") || text.includes("HTTP/1.1\" 304") || text.includes("HTTP/1.1\" 302")) {
      console.log(`[Django Access] ${text}`);
    } else {
      console.error(`[Django Error] ${text}`);
    }
  });

  djangoProcess.on("error", (err) => {
    console.error(`[Django Process Error] ${err.message}`);
    isDjangoReady = false;
  });

  djangoProcess.on("exit", (code, signal) => {
    console.log(`[Django] Exited with code ${code} signal ${signal}`);
    isDjangoReady = false;
    if (!isShuttingDown) {
      // Auto-restart Django if it ever terminates unexpectedly
      setTimeout(() => {
        console.log("[Proxy] Re-spawning Django server process...");
        startDjangoServer();
      }, 1500);
    }
  });
}

function checkDjangoHealth(retries = 30, delayMs = 1000): Promise<void> {
  return new Promise((resolve) => {
    let attempts = 0;
    const interval = setInterval(() => {
      attempts++;
      const req = http.get(`http://${DJANGO_HOST}:${DJANGO_PORT}/`, (res) => {
        isDjangoReady = true;
        clearInterval(interval);
        console.log(`[Proxy] Django is online and accepting requests (status ${res.statusCode})`);
        resolve();
      });

      req.on("error", () => {
        if (attempts >= retries) {
          clearInterval(interval);
          console.log("[Proxy] Max healthcheck retries reached; proceeding.");
          resolve();
        }
      });
      req.end();
    }, delayMs);
  });
}

ensurePythonEnvironment();
startDjangoServer();

// Health check endpoint
app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    djangoReady: isDjangoReady,
    service: "Kabale University IDR Discovery & Analytics Platform",
  });
});

// Proxy middleware targeting Django
const djangoProxy = createProxyMiddleware({
  target: `http://${DJANGO_HOST}:${DJANGO_PORT}`,
  changeOrigin: true,
  ws: true,
  on: {
    proxyRes: (proxyRes) => {
      delete proxyRes.headers["x-frame-options"];
      delete proxyRes.headers["cross-origin-opener-policy"];
    },
    error: (err, req, res) => {
      console.error("[Proxy Error]", err.message);
      const httpRes = res as http.ServerResponse;
      if (!httpRes.headersSent) {
        httpRes.writeHead(502, { "Content-Type": "text/html" });
        httpRes.end(`
          <html>
            <head><title>Loading Platform...</title><meta http-equiv="refresh" content="2"></head>
            <body style="font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f8faf9; color: #0d5c3a;">
              <div style="text-align: center; padding: 2rem; border: 1px solid #e2e8f0; border-radius: 8px; background: white; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                <h2 style="margin: 0 0 10px 0;">Kabale University Research Portal</h2>
                <p style="color: #64748b; margin: 0;">Starting Django research services... Refreshing automatically.</p>
              </div>
            </body>
          </html>
        `);
      }
    },
  },
});

app.use("/", djangoProxy);

const server = app.listen(PORT, "0.0.0.0", () => {
  console.log(`[Server] Proxy server listening on http://0.0.0.0:${PORT}`);
  checkDjangoHealth();
});

function cleanup() {
  isShuttingDown = true;
  if (djangoProcess) {
    console.log("[Cleanup] Terminating Django process...");
    djangoProcess.kill("SIGTERM");
  }
  server.close(() => {
    process.exit(0);
  });
}

process.on("SIGTERM", cleanup);
process.on("SIGINT", cleanup);
