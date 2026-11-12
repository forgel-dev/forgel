// Acceptance scenario for the hello-web M0 product.

export async function run({ page, baseUrl, check }) {
  await page.goto(baseUrl, { waitUntil: 'networkidle2' })

  const title = await page.title()
  const heading = await page.$eval('h1', element => element.textContent.trim())

  const health = await page.evaluate(async () => {
    const response = await fetch('/health')
    return { status: response.status, body: await response.json() }
  })

  check('index mentions project', title.includes('__PROJECT_NAME__'), title)
  check('index heading', heading.includes('__PROJECT_NAME__'), heading)
  check('health status 200', health.status === 200, String(health.status))
  check('health body ok', health.body.status === 'ok', JSON.stringify(health.body))
}
