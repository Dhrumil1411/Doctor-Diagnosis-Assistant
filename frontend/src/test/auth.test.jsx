import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../context/AuthContext.jsx";
import LoginPage from "../pages/LoginPage.jsx";
import { api } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  api: {
    get: vi.fn(),
    postForm: vi.fn(),
  },
  getToken: vi.fn(() => null),
  setToken: vi.fn(),
}));

describe("Login Flow", () => {
  it("renders login form with email and password inputs", () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign In/i })).toBeInTheDocument();
  });

  it("submits login credentials successfully", async () => {
    const user = userEvent.setup();
    api.postForm.mockResolvedValueOnce({ access_token: "mock-token-xyz" });
    api.get.mockResolvedValueOnce({ id: "u-1", email: "doctor@example.com", role: "doctor" });

    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    await user.type(screen.getByLabelText(/Email Address/i), "doctor@example.com");
    await user.type(screen.getByLabelText(/Password/i), "Secret123!");
    await user.click(screen.getByRole("button", { name: /Sign In/i }));

    await waitFor(() => {
      expect(api.postForm).toHaveBeenCalledWith("/auth/login", {
        username: "doctor@example.com",
        password: "Secret123!",
      });
    });
  });

  it("displays error message when login fails", async () => {
    const user = userEvent.setup();
    api.postForm.mockRejectedValueOnce({ status: 401, message: "Unauthorized" });

    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    await user.type(screen.getByLabelText(/Email Address/i), "wrong@example.com");
    await user.type(screen.getByLabelText(/Password/i), "WrongPass!");
    await user.click(screen.getByRole("button", { name: /Sign In/i }));

    await waitFor(() => {
      expect(screen.getByText(/Incorrect email or password/i)).toBeInTheDocument();
    });
  });
});
