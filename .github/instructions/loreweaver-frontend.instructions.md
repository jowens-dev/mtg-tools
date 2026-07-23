---
description: React frontend rules and backend API mapping for the Loreweaver app.
applyTo:
  - "src/**/*.jsx"
  - "src/**/*.js"
---

# Loreweaver Architecture & Rules

## 1. UI & Styling (Tailwind)
- Always use modern Tailwind CSS classes.
- Default to a dark mode aesthetic (e.g., `bg-gray-900`, `bg-gray-800`, `text-white`, and indigo/violet accents).
- Do not use inline CSS; keep styles in the `className` string.

## 2. API & Data Fetching
- The Python backend runs locally on port 8000.
- Base API URL: `http://localhost:8000/api`
- To fetch Commander recommendations, use: `GET /api/recommendations?commander={commanderName}`
- The backend returns an array of card objects. Each card object includes properties like `name`, `image_url`, `cmc`, and a `spice_score`.

## 3. The "Flavor/Spice" Concept (Crucial Domain Logic)
- In this application, deck "flavor" does not mean strict adherence to a set or fictional lore.
- "Flavor" or "Spice" means a sprinkle of uniqueness that still makes mechanical sense—specifically straying away from mainstream, cookie-cutter optimal staples.
- A high spice score (e.g., EDHREC rank > 5000) means it's a deep cut. A low spice score means it is a predictable staple.
- When building UI elements related to "Spice Level", ensure the logic de-emphasizes (fades out or filters) low-spice staples as the user increases the dial.

## 4. State & Structure
- Use functional React components and Hooks (`useState`, `useEffect`).
- For the active decklist drawer, always store full card objects in state (not just string names) so the UI can calculate average CMC and render card art previews on hover.
