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

test("formatDate preserves local variants and UTC chart labels", () => {
  const timestamp = "2026-06-25T00:30:00.000Z";
  const date = new Date(timestamp);

  assert.equal(
    formatDate(timestamp),
    date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
  );
  assert.equal(formatDate(timestamp, "dateOnly"), date.toLocaleDateString());
  assert.equal(formatDate(timestamp, "monthDay"), "Jun 25");
  assert.equal(
    formatDate(timestamp, "numericDateTime"),
    date.toLocaleString(),
  );
});
