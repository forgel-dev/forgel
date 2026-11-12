#!/usr/bin/env node
// Headless-browser runner, ported from the Gapi QA pattern:
// a Docker stand for the product, Puppeteer with a system Chrome for the checks.

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import puppeteer from 'puppeteer-core'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean)
  return candidates.find(candidate => fs.existsSync(candidate))
}

function argValue(name, fallback) {
  const index = process.argv.indexOf(name)
  return index === -1 ? fallback : process.argv[index + 1]
}

const baseUrl = argValue(
  '--base-url',
  process.env.QA_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '')
const scenarioName = argValue('--scenario', 'hello_web.mjs')
const scenarioPath = path.resolve(__dirname, 'scenarios', scenarioName)
const chromePath = findChrome()

if (!chromePath) {
  console.error('Chrome not found. Set CHROME_PATH to a Chrome/Chromium binary.')
  process.exit(2)
}
if (!fs.existsSync(scenarioPath)) {
  console.error(`Scenario not found: ${scenarioPath}`)
  process.exit(2)
}

const checks = []

function check(name, condition, detail = '') {
  checks.push({ name, ok: Boolean(condition), detail })
  console.log(`${condition ? 'PASS' : 'FAIL'} ${name}${detail ? ` [${detail}]` : ''}`)
  return Boolean(condition)
}

const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
})

try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1280, height: 900 })

  const errors = []
  page.on('console', message => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`)
  })
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`))

  const scenario = await import(pathToFileURL(scenarioPath).href)
  await scenario.run({ page, baseUrl, check })

  check('no browser errors', errors.length === 0, errors.join('; '))
} finally {
  await browser.close()
}

const failed = checks.filter(item => !item.ok)
console.log(`SUMMARY: ${checks.length - failed.length}/${checks.length} checks passed`)
process.exit(failed.length === 0 ? 0 : 1)
