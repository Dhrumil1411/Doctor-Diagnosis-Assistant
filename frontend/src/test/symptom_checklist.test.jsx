import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import SymptomChecklist from "../components/SymptomChecklist.jsx";
import { api } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  api: {
    get: vi.fn(),
  },
}));

const MOCK_VOCABULARY = [
  { id: "cough", display_name: "Cough", category: "Respiratory", hpo_id: "HP:0012735" },
  { id: "fever", display_name: "Fever", category: "Constitutional", hpo_id: "HP:0001945" },
  { id: "chest_pain", display_name: "Chest Pain", category: "Cardiovascular", hpo_id: "HP:0100749" },
];

describe("SymptomChecklist Component", () => {
  it("fetches symptom vocabulary on mount and renders search box", async () => {
    api.get.mockResolvedValueOnce(MOCK_VOCABULARY);

    render(<SymptomChecklist entries={[]} onChange={() => {}} />);

    expect(screen.getByLabelText(/Search symptoms/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/symptom-vocabulary");
    });
  });

  it("filters vocabulary by search query and allows adding symptom", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValueOnce(MOCK_VOCABULARY);
    const onChange = vi.fn();

    render(<SymptomChecklist entries={[]} onChange={onChange} />);

    await waitFor(() => expect(api.get).toHaveBeenCalled());

    const searchInput = screen.getByLabelText(/Search symptoms/i);
    await user.type(searchInput, "cough");

    await waitFor(() => {
      expect(screen.getByText("Cough")).toBeInTheDocument();
    });

    const addBtn = screen.getByRole("button", { name: /\+.*Cough/i });
    await user.click(addBtn);

    expect(onChange).toHaveBeenCalledWith([
      { name: "cough", status: "present", severity: "", duration: "" },
    ]);
  });

  it("allows removing a selected symptom from active entries", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValueOnce(MOCK_VOCABULARY);
    const onChange = vi.fn();

    const activeEntries = [
      { name: "fever", status: "present", severity: 7, duration: "2 days" },
    ];

    render(<SymptomChecklist entries={activeEntries} onChange={onChange} />);

    await waitFor(() => expect(api.get).toHaveBeenCalled());

    const removeBtn = screen.getByRole("button", { name: /Remove Fever/i });
    await user.click(removeBtn);

    expect(onChange).toHaveBeenCalledWith([]);
  });
});
