import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import App from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { api, getToken } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    postForm: vi.fn(),
  },
  getToken: vi.fn(),
  setToken: vi.fn(),
}));

describe("Routing & Protected Route Redirects", () => {
  it("redirects unauthenticated users from protected home route to /login", async () => {
    getToken.mockReturnValue(null);

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Sign In/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    });
  });

  it("renders protected content when user is authenticated", async () => {
    getToken.mockReturnValue("valid-jwt-token");
    api.get.mockImplementation((url) => {
      if (url === "/auth/me") {
        return Promise.resolve({
          id: "u-1",
          email: "doc@clinic.org",
          full_name: "Dr. Smith",
          role: "doctor",
        });
      }
      if (url === "/patients") {
        return Promise.resolve([]);
      }
      return Promise.resolve({});
    });

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Clinical Encounters & Patient Records/i)).toBeInTheDocument();
      expect(screen.getByText(/Start New Consultation/i)).toBeInTheDocument();
    });
  });
});
