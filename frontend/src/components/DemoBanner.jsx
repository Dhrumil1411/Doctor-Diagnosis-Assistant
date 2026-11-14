import React from "react";

export default function DemoBanner({ inline = false }) {
  const isDemo =
    import.meta.env?.VITE_DEMO_MODE === "true" ||
    import.meta.env?.VITE_DEMO_MODE === true;

  if (!isDemo) return null;

  return (
    <div
      role="alert"
      className="demo-banner"
      style={
        inline
          ? {
              backgroundColor: "#fef3c7",
              color: "#92400e",
              border: "1px solid #fcd34d",
              borderRadius: "8px",
              padding: "0.6rem 0.85rem",
              fontSize: "0.82rem",
              fontWeight: "600",
              textAlign: "center",
              marginBottom: "1.25rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.4rem",
            }
          : {
              backgroundColor: "#fef3c7",
              color: "#92400e",
              borderBottom: "1px solid #fcd34d",
              padding: "0.35rem 1rem",
              fontSize: "0.8rem",
              fontWeight: "600",
              textAlign: "center",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.5rem",
              width: "100%",
            }
      }
    >
      <span aria-hidden="true">⚠️</span>
      <span>Demo — synthetic data only, not medical advice</span>
    </div>
  );
}
