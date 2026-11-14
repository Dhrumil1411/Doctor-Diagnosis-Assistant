import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import NewVisitPage from "../pages/NewVisitPage.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { api } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  getToken: vi.fn(() => "mock-jwt"),
  setToken: vi.fn(),
}));

describe("Intake Form Validation & Calculations", () => {
  it("rejects form submission and shows validation error when full name is empty", async () => {
    const user = userEvent.setup();
    api.get.mockImplementation((url) => {
      if (url === "/auth/me") {
        return Promise.resolve({ id: "u-1", email: "doctor@hospital.org", role: "doctor" });
      }
      if (url === "/symptom-vocabulary") {
        return Promise.resolve([]);
      }
      return Promise.resolve([]);
    });

    render(
      <BrowserRouter>
        <AuthProvider>
          <NewVisitPage />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/New consultation/i)).toBeInTheDocument();
    });

    // Attempt submission with empty name
    const submitBtn = screen.getByRole("button", { name: /Save consultation/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Patient full name is required.");
    });
    expect(api.post).not.toHaveBeenCalled();
  });

  it("dynamically calculates BMI when valid weight and height are entered", async () => {
    const user = userEvent.setup();
    api.get.mockImplementation((url) => {
      if (url === "/auth/me") {
        return Promise.resolve({ id: "u-1", email: "doctor@hospital.org", role: "doctor" });
      }
      return Promise.resolve([]);
    });

    render(
      <BrowserRouter>
        <AuthProvider>
          <NewVisitPage />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/New consultation/i)).toBeInTheDocument();
    });

    // Enter weight = 70 kg, height = 175 cm -> BMI should be 70 / (1.75^2) = 22.9
    const weightInput = screen.getByLabelText(/Weight \(kg\)/i);
    const heightInput = screen.getByLabelText(/Height \(cm\)/i);

    await user.type(weightInput, "70");
    await user.type(heightInput, "175");

    await waitFor(() => {
      expect(screen.getByText(/BMI 22.9/i)).toBeInTheDocument();
    });
  });
});
