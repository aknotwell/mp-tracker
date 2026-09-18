import "@testing-library/jest-dom/vitest";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "./page";

describe("HomePage", () => {
  it("identifies the application scaffold", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", { name: "Fragrance Collection Tracker" }),
    ).toBeInTheDocument();
  });
});
