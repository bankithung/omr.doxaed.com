import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import { AuthProvider } from "@/auth/AuthContext"
import { OrgProvider } from "@/org/OrgContext"
import { ThemeProvider } from "@/components/ThemeProvider"
import App from "./App.jsx"
import "@fontsource/geist-mono/400.css"
import "@fontsource/geist-mono/500.css"
import "./index.css"

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <OrgProvider>
            <App />
          </OrgProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
