//import React from 'react'
import App from './App'
import './index.css'
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

const el = document.getElementById("root");
if (!el) {
  throw new Error("Root element #root not found");
}
createRoot(el).render(
  <StrictMode>
    <App />
  </StrictMode>
);

createRoot(document.getElementById('root')!).render(<App />);
