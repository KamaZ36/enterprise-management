import { execSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8000";
const here = dirname(fileURLToPath(import.meta.url));
const openapiPath = resolve(here, "../openapi.json");
const schemaPath = resolve(here, "../packages/api-client/src/schema.d.ts");

const response = await fetch(`${apiUrl}/openapi.json`);

if (!response.ok) {
  throw new Error(`Не удалось получить схему: ${response.status}`);
}

const spec = await response.json();
writeFileSync(openapiPath, `${JSON.stringify(spec, null, 2)}\n`);
console.log(`openapi.json обновлён, путей: ${Object.keys(spec.paths).length}`);

execSync(`pnpm exec openapi-typescript ${openapiPath} -o ${schemaPath}`, {
  cwd: resolve(here, ".."),
  stdio: "inherit",
});

console.log("schema.d.ts собран");
