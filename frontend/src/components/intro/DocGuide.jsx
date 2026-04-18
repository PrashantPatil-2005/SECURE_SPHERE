/**
 * How to read the wireframe document — same intent as the original list.
 */
export default function DocGuide() {
  return (
    <ul className="list-disc space-y-2 pl-5 text-sm text-base-300">
      <li>Each tab = one screen</li>
      <li>Cards group related controls and context; spacing is intentional, not decoration.</li>
      <li>Arrows show dependency and attack direction, not necessarily live traffic volume.</li>
      <li>Severity coloring is consistent across wireframes and the shipped console.</li>
      <li>Blue accents mark interactive focus and navigation affordances, not decorative chrome.</li>
      <li>Where numbers appear, treat them as illustrative unless tied to a live data contract.</li>
    </ul>
  );
}
