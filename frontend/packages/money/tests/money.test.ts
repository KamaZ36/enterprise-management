import { describe, expect, it } from "vitest";

import {
  formatKopecks,
  formatKopecksShort,
  formatQuantity,
  parseRublesToKopecks,
} from "../src/index";

describe("formatKopecks", () => {
  it("показывает копейки двумя знаками", () => {
    expect(formatKopecks(45000)).toContain("450,00");
    expect(formatKopecks(45012)).toContain("450,12");
    expect(formatKopecks(5)).toContain("0,05");
  });

  it("разделяет тысячи", () => {
    expect(formatKopecksShort(123456789)).toBe("1\u00a0234\u00a0567,89");
  });

  it("не теряет точность на больших суммах", () => {
    expect(formatKopecksShort(9007199254740991)).toBe(
      "90\u00a0071\u00a0992\u00a0547\u00a0409,91",
    );
  });

  it("обрабатывает ноль и пустое значение", () => {
    expect(formatKopecksShort(0)).toBe("0,00");
    expect(formatKopecks(null)).toBe("—");
    expect(formatKopecks(undefined)).toBe("—");
  });

  it("ставит минус перед суммой", () => {
    expect(formatKopecksShort(-12345)).toBe("−123,45");
  });
});

describe("parseRublesToKopecks", () => {
  it("принимает рубли и копейки", () => {
    expect(parseRublesToKopecks("1234")).toBe(123400);
    expect(parseRublesToKopecks("1234,5")).toBe(123450);
    expect(parseRublesToKopecks("1234.56")).toBe(123456);
    expect(parseRublesToKopecks("0,05")).toBe(5);
  });

  it("понимает пробелы, неразрывный пробел и знак рубля", () => {
    expect(parseRublesToKopecks("1 234,50")).toBe(123450);
    expect(parseRublesToKopecks("1\u00a0234,50 ₽")).toBe(123450);
  });

  it("возвращает null на мусоре", () => {
    expect(parseRublesToKopecks("")).toBeNull();
    expect(parseRublesToKopecks("двенадцать")).toBeNull();
    expect(parseRublesToKopecks("12,345")).toBeNull();
    expect(parseRublesToKopecks(null)).toBeNull();
  });

  it("переживает обратный разбор без потери копейки", () => {
    for (const kopecks of [0, 5, 99, 45012, 123456789]) {
      expect(parseRublesToKopecks(formatKopecksShort(kopecks))).toBe(kopecks);
    }
  });
});

describe("formatQuantity", () => {
  it("приходит строкой из API и не превращается в мусор", () => {
    expect(formatQuantity("10.000000")).toBe("10");
    expect(formatQuantity("10.500000")).toBe("10,5");
    expect(formatQuantity("0.001000")).toBe("0,001");
  });

  it("обрабатывает пустое значение", () => {
    expect(formatQuantity(null)).toBe("—");
    expect(formatQuantity("")).toBe("—");
    expect(formatQuantity("abc")).toBe("—");
  });
});
