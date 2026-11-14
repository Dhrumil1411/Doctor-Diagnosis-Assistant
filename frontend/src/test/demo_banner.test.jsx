import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import DemoBanner from "../components/DemoBanner.jsx";

describe("DemoBanner Component", () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it("does not render when VITE_DEMO_MODE is false or not set", () => {
    vi.stubEnv("VITE_DEMO_MODE", "false");
    const { container } = render(<DemoBanner />);
    expect(container.firstChild).toBeNull();
    expect(screen.queryByText(/Demo — synthetic data only, not medical advice/i)).not.toBeInTheDocument();
  });

  it("renders visible disclaimer banner when VITE_DEMO_MODE is true", () => {
    vi.stubEnv("VITE_DEMO_MODE", "true");
    render(<DemoBanner />);
    const banner = screen.getByText(/Demo — synthetic data only, not medical advice/i);
    expect(banner).toBeInTheDocument();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
