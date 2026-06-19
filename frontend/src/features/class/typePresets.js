// Default level labels per org type — seeds the nested-group tree. Every node is
// renamable, so these are only defaults / sensible starting points.
export const TYPE_PRESETS = {
  school: ["Class", "Section"],
  college: ["Course", "Year", "Section"],
  university: ["Department", "Program", "Batch"],
  coaching: ["Batch", "Section"],
  personal: ["Group"],
  other: ["Group"],
}

const FALLBACK = "Group"

function preset(orgType) {
  return TYPE_PRESETS[orgType] ?? TYPE_PRESETS.other
}

// Label for a TOP-LEVEL node (a "Class", "Department", …).
export function topKindLabel(orgType) {
  return preset(orgType)[0] ?? FALLBACK
}

// Default label for a CHILD of a node whose own label is parentKindLabel.
export function childKindLabel(orgType, parentKindLabel) {
  const p = preset(orgType)
  const idx = p.indexOf(parentKindLabel)
  if (idx === -1) return FALLBACK
  return p[idx + 1] ?? FALLBACK
}

// Naive English pluralize for nav/headings (Section→Sections, Year→Years,
// Class→Classes via the -s/-es rule below… "Class" → "Classes").
export function pluralize(label) {
  if (!label) return "Sub-groups"
  if (/[sxz]$|[cs]h$/i.test(label)) return label + "es" // Class→Classes, Batch→Batches
  if (/[^aeiou]y$/i.test(label)) return label.replace(/y$/i, "ies") // Year→Years? no — Category→Categories
  return label + "s"
}
