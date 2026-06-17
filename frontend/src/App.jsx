import { Link, Route, Routes } from "react-router-dom"
import Health from "@/routes/Health"
import StyleGuide from "@/routes/StyleGuide"

export default function App() {
  return (
    <div>
      <nav className="flex gap-4 p-4 border-b">
        <Link to="/health">Health</Link>
        <Link to="/style-guide">Style Guide</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Health />} />
        <Route path="/health" element={<Health />} />
        <Route path="/style-guide" element={<StyleGuide />} />
      </Routes>
    </div>
  )
}
