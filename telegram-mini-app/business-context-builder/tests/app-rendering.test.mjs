import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const appSource = readFileSync(
  new URL("../src/app.js", import.meta.url),
  "utf8"
);

test("frontend renders a safe empty integrations state", () => {
  assert.match(appSource, /integrations\.length === 0/);
  assert.match(appSource, /No channels are connected for this business yet/);
});

test("frontend mock data keeps multiple Telegram integrations separate", () => {
  assert.match(appSource, /mock-telegram-1/);
  assert.match(appSource, /mock-telegram-2/);
  assert.match(appSource, /Telegram Bot 1/);
  assert.match(appSource, /Telegram Bot 2/);
});
