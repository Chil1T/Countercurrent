import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workbenchSource = readFileSync(
  new URL("../components/results/results-workbench.tsx", import.meta.url),
  "utf8"
);

test("results workbench includes an explicit UI toggle for filtered export", () => {
  assert.match(workbenchSource, /只导出已完成章节/);
  assert.match(workbenchSource, /finalOutputsOnly: exportFinalOnly/);
});

test("results workbench keeps full export as the default behavior", () => {
  assert.match(workbenchSource, /const \[exportCompletedOnly, setExportCompletedOnly\] = useState\(false\)/);
  assert.match(workbenchSource, /const \[exportFinalOnly, setExportFinalOnly\] = useState\(false\)/);
});

test("results workbench preserves selection and expansion rather than blindly expanding all", () => {
  // It shouldn't force collectTreeSectionKeys(nextTree) on SSE update anymore
  assert.doesNotMatch(workbenchSource, /setExpandedKeys\(\(current\) => new Set\(\[\.\.\.current, \.\.\.nextExpandedKeys\]\)\)/);
});
