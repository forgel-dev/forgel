// Headless-browser scenario for the isolated QA stand.
//
// It loads the SPA served by the web service, waits for the health request the
// SPA performs, asserts that the API answered 200 with {"status": "ok"} and
// asserts that the rendered page shows the health status text. Every check is
// printed; the process exits non-zero when a check fails.
const { chromium } = require("playwright-core");

const BASE_URL = process.env.BASE_URL || "http://web:8080";
const STEP_TIMEOUT = Number(process.env.STEP_TIMEOUT || "20000");
const CHROMIUM_PATH = process.env.CHROMIUM_PATH || "/usr/bin/chromium";

const checks = [];

function check(name, passed, detail) {
  const ok = Boolean(passed);
  checks.push({ name, ok });
  const suffix = detail === undefined || detail === "" ? "" : ` [${detail}]`;
  console.log(`${ok ? "PASS" : "FAIL"} ${name}${suffix}`);
  return ok;
}

async function scenario() {
  const browser = await chromium.launch({
    executablePath: CHROMIUM_PATH,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage();
  try {
    const healthRequest = page.waitForResponse(
      (response) => new URL(response.url()).pathname === "/healthz",
      { timeout: STEP_TIMEOUT }
    );

    const index = await page.goto(`${BASE_URL}/`, {
      waitUntil: "load",
      timeout: STEP_TIMEOUT,
    });
    check(
      "the SPA index returns 200",
      index !== null && index.status() === 200,
      index === null ? "no response" : String(index.status())
    );

    const health = await healthRequest;
    check(
      "the API request /healthz returns 200",
      health.status() === 200,
      String(health.status())
    );
    const body = await health.json().catch(() => ({}));
    check(
      'the API answers {"status": "ok"}',
      body.status === "ok",
      JSON.stringify(body)
    );

    const status = page.getByTestId("health-status");
    await status.waitFor({ state: "visible", timeout: STEP_TIMEOUT });
    await page.waitForFunction(
      () => {
        const node = document.querySelector('[data-testid="health-status"]');
        return node !== null && node.textContent.trim() === "ok";
      },
      undefined,
      { timeout: STEP_TIMEOUT }
    );

    const text = ((await page.getByTestId("health").textContent()) || "")
      .replace(/\s+/g, " ")
      .trim();
    check(
      "the SPA renders the health status text",
      /Health: ok/.test(text),
      text
    );
    check("the SPA renders the HTTP status code", /HTTP 200/.test(text), text);
  } finally {
    await browser.close();
  }
}

scenario()
  .then(() => {
    const failed = checks.filter((item) => !item.ok);
    console.log(
      `SUMMARY: ${checks.length - failed.length}/${checks.length} checks passed`
    );
    process.exit(failed.length === 0 ? 0 : 1);
  })
  .catch((error) => {
    console.log(`FAIL the scenario did not finish [${error}]`);
    console.log("SUMMARY: 0/1 checks passed");
    process.exit(1);
  });
