export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ru-RU").format(date);
}

export function fullName(person: {
  last_name: string;
  first_name: string;
  middle_name?: string | null;
}): string {
  return [person.last_name, person.first_name, person.middle_name]
    .filter(Boolean)
    .join(" ");
}

export function shortId(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  return `${value.slice(0, 8)}…`;
}
