"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const app = require("./app.js");

function close(a, b) { assert.ok(Math.abs(a - b) < 1e-8 * Math.max(1, Math.abs(b)), `${a} !== ${b}`); }

test("matched spot urine measurements", () => {
  const r = app.calculate({ protein_mg_dl: 20, albumin_mg_dl: 5, creatinine_mg_dl: 100 });
  close(r.upcr_mg_g, 200);
  close(r.uacr_mg_g, 50);
  close(r.upcr_mg_mmol, 22.624);
  close(r.albumin_fraction_percent, 25);
  assert.match(r.albuminuria_category, /^A2/);
});
test("ratio units round-trip", () => {
  close(app.toMgG(30 * app.CREATININE_G_PER_MMOL, "mg/mmol"), 30);
});
test("threshold boundaries", () => {
  for (const [val, cat] of [[0,"A1"],[29.999,"A1"],[30,"A2"],[299.999,"A2"],[300,"A3"]]) {
    assert.match(app.calculate({uacr_mg_g:val}).albuminuria_category, new RegExp("^" + cat));
  }
});
test("cannot infer albumin from total protein", () => {
  const r = app.calculate({upcr_mg_g:100});
  assert.equal(r.uacr_mg_g, null);
  assert.equal(r.albuminuria_category, null);
});
test("optional 24-hour estimate", () => {
  const r = app.calculate({upcr_mg_g:100, uacr_mg_g:25, creatinine_g_day:1.2});
  close(r.estimated_protein_mg_day, 120);
  close(r.estimated_albumin_mg_day, 30);
  assert.ok(r.warnings.length > 0);
});
test("discordance is flagged", () => {
  assert.ok(app.calculate({upcr_mg_g:50,uacr_mg_g:60}).warnings.length > 0);
});
test("invalid measurements fail without fabricating data", () => {
  for (const data of [
    {}, {protein_mg_dl:20}, {protein_mg_dl:10,creatinine_mg_dl:0},
    {uacr_mg_g:-1}, {uacr_mg_g:Infinity}, {uacr_mg_g:NaN},
    {uacr_mg_g:30,albumin_mg_dl:2,creatinine_mg_dl:100},
    {uacr_mg_g:20,creatinine_g_day:0}
  ]) assert.throws(() => app.calculate(data));
});
