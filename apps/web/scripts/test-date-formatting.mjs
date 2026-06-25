import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import ts from "typescript";

const require = createRequire(import.meta.url);
const source = readFileSync(new URL("../src/lib/utils.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: {
    esModuleInterop: true,
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
});

const utilsModule = { exports: {} };

new Function("exports", "require", "module", outputText)(
  utilsModule.exports,
  require,
  utilsModule,
);

const { formatDate } = utilsModule.exports;

test("formatDate keeps UTC boundary timestamps deterministic", () => {
  const timestamp = "2026-06-25T00:30:00.000Z";

  assert.equal(formatDate(timestamp), "Jun 25, 12:30 AM");
  assert.equal(formatDate(timestamp, "dateOnly"), "6/25/2026");
  assert.equal(formatDate(timestamp, "monthDay"), "Jun 25");
  assert.equal(
    formatDate(timestamp, "numericDateTime"),
    "6/25/2026, 12:30:00 AM",
  );
});
