const TRANSLIT: Record<string, string> = {
  а: "a",
  б: "b",
  в: "v",
  г: "g",
  д: "d",
  е: "e",
  ё: "e",
  ж: "zh",
  з: "z",
  и: "i",
  й: "y",
  к: "k",
  л: "l",
  м: "m",
  н: "n",
  о: "o",
  п: "p",
  р: "r",
  с: "s",
  т: "t",
  у: "u",
  ф: "f",
  х: "h",
  ц: "c",
  ч: "ch",
  ш: "sh",
  щ: "sch",
  ъ: "",
  ы: "y",
  ь: "",
  э: "e",
  ю: "yu",
  я: "ya",
};

/**
 * Код техкарты из названия: «Докторская 50/50» → «DOKTORSKAYA-50-50».
 *
 * Код общий для редакций: одно и то же название даёт тот же код, поэтому
 * повторное создание техкарты становится новой версией, а не дублем.
 */
export function slugify(value: string): string {
  return transliterate(value)
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64)
    .replace(/-+$/g, "")
    .toUpperCase();
}

/**
 * Логин сотрудника из ФИО: «Струк» + «Елена» → «struk_elena».
 */
export function loginFromName(lastName: string, firstName: string): string {
  const part = (value: string): string =>
    transliterate(value)
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "");

  return [part(lastName), part(firstName)]
    .filter(Boolean)
    .join("_")
    .slice(0, 64);
}

function transliterate(value: string): string {
  return Array.from(value.toLowerCase())
    .map((char) => TRANSLIT[char] ?? char)
    .join("");
}
