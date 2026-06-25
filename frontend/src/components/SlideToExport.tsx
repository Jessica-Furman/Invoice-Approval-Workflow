import { useEffect, useRef, useState } from "react";
import { ChevronsRight, Loader2 } from "lucide-react";

const KNOB = 32; // px — knob diameter
const PAD = 3; // px — track inner padding
const THRESHOLD = 0.9; // fraction of travel needed to fire

/** A "slide to confirm" control: drag the green knob to the right "Export All" end to trigger.
 *  Snaps back if released before the threshold. Disabled (and dimmed) when there's nothing to export. */
export function SlideToExport({
  count,
  pending,
  onExport,
}: {
  count: number;
  pending: boolean;
  onExport: () => void;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [x, setX] = useState(0);
  const [dragging, setDragging] = useState(false);
  const disabled = count === 0 || pending;

  const maxX = () => Math.max(0, (trackRef.current?.clientWidth ?? 240) - KNOB - PAD * 2);

  // Reset the knob whenever export finishes or the set of matched invoices changes.
  useEffect(() => {
    setX(0);
  }, [count, pending]);

  function move(clientX: number) {
    const rect = trackRef.current?.getBoundingClientRect();
    if (!rect) return;
    const nx = Math.min(Math.max(clientX - rect.left - KNOB / 2, 0), maxX());
    setX(nx);
  }

  function onPointerDown(e: React.PointerEvent) {
    if (disabled) return;
    setDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  function onPointerMove(e: React.PointerEvent) {
    if (dragging) move(e.clientX);
  }
  function onPointerUp() {
    if (!dragging) return;
    setDragging(false);
    if (x >= maxX() * THRESHOLD) {
      setX(maxX());
      onExport();
    } else {
      setX(0);
    }
  }

  const pct = maxX() > 0 ? x / maxX() : 0;

  return (
    <div
      ref={trackRef}
      className={`relative h-10 w-full select-none overflow-hidden rounded-full border transition ${
        disabled
          ? "cursor-not-allowed border-slate-200 bg-slate-100"
          : "border-emerald-300 bg-emerald-100"
      }`}
      title={count === 0 ? "No matched invoices to export" : "Slide right to export all matched invoices"}
    >
      {/* Green fill that grows as you slide */}
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-emerald-500"
        style={{ width: x + KNOB + PAD, opacity: disabled ? 0.4 : 0.9, transition: dragging ? "none" : "width 200ms" }}
      />

      {/* Right-aligned label */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-end pr-4">
        <span className={`text-sm font-bold ${pct > 0.55 ? "text-white" : disabled ? "text-slate-400" : "text-emerald-700"}`}>
          {pending ? "Exporting…" : `Export All${count ? ` (${count})` : ""}`}
        </span>
      </div>

      {/* Draggable knob */}
      <div
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        className={`absolute top-1/2 flex items-center justify-center rounded-full bg-white shadow-md ${
          disabled ? "" : "cursor-grab active:cursor-grabbing"
        }`}
        style={{
          width: KNOB,
          height: KNOB,
          left: PAD + x,
          transform: "translateY(-50%)",
          transition: dragging ? "none" : "left 200ms",
        }}
      >
        {pending ? (
          <Loader2 className="h-4 w-4 animate-spin text-emerald-600" />
        ) : (
          <ChevronsRight className={`h-5 w-5 ${disabled ? "text-slate-300" : "text-emerald-600"}`} />
        )}
      </div>
    </div>
  );
}
