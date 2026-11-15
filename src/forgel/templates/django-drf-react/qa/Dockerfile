# Headless browser for the QA scenario: Chromium from the Alpine packages,
# driven by the ``playwright-core`` client. No browser is downloaded at run
# time, and the image stays small enough for a local stand.
FROM node:22-alpine

RUN apk add --no-cache chromium

ENV NODE_ENV=production \
    CHROMIUM_PATH=/usr/bin/chromium

WORKDIR /qa

COPY package.json /qa/package.json
RUN npm install --no-audit --no-fund

COPY scenario.js /qa/scenario.js

CMD ["node", "/qa/scenario.js"]
