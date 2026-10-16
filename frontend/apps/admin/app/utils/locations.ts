import type { components } from "@md/api-client";

export type Location = components["schemas"]["LocationSchema"];

export function locationDisplay(location: Location | null | undefined): string {
  if (!location) {
    return "—";
  }

  return location.name;
}
