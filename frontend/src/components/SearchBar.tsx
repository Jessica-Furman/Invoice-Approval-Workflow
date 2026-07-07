import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Building2, Hash, Search } from "lucide-react";
import { fetchDashboard } from "../api/client";

/**
 * Search box for the header: filters the board by vendor or invoice ID, with
 * - inline "ghost" autocomplete that predicts a known vendor as you type (accept with Tab / →), and
 * - a suggestions dropdown of matching vendors (with counts) and invoice IDs.
 *
 * Suggestions come from the cached dashboard query, so it shares data with the board (no extra fetch).
 */
export function SearchBar({
  value,
  onChange,
  dark = false,
}: {
  value: string;
  onChange: (v: string) => void;
  dark?: boolean;
}) {
  const { data } = useQuery({ queryKey: ["dashboard"], queryFn: fetchDashboard });
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const all = data?.all ?? [];
  const q = value.trim().toLowerCase();

  const vendors = useMemo(
    () => Array.from(new Set(all.map((i) => i.vendor_name).filter(Boolean) as string[])).sort(),
    [all]
  );

  // Inline prediction: first known vendor that starts with what's typed (case-insensitive).
  // Suggestions come from the CONTRACTOR board, so they're suppressed on the dark ("other") board.
  const ghostVendor = q && !dark ? vendors.find((v) => v.toLowerCase().startsWith(q)) : undefined;
  const ghost = ghostVendor && ghostVendor.length > value.length ? ghostVendor.slice(value.length) : "";

  const vendorMatches = q ? vendors.filter((v) => v.toLowerCase().includes(q)).slice(0, 6) : [];
  const idMatches = q
    ? all
        .filter(
          (i) =>
            (i.invoice_number ?? "").toLowerCase().includes(q) || String(i.id) === q
        )
        .slice(0, 6)
    : [];
  const showDropdown = !dark && open && q.length > 0 && (vendorMatches.length > 0 || idMatches.length > 0);

  function acceptGhost() {
    if (ghostVendor) {
      onChange(ghostVendor);
      setOpen(false);
    }
  }

  return (
    <div className="relative w-full max-w-xl">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />

      {/* Ghost overlay — mirrors the input's box model so the prediction lines up exactly. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 flex items-center whitespace-pre border border-transparent pl-10 pr-4 text-sm"
      >
        <span className="invisible">{value}</span>
        <span className="text-slate-400">{ghost}</span>
      </div>

      <input
        ref={inputRef}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={(e) => {
          if ((e.key === "Tab" || e.key === "ArrowRight") && ghost) {
            const atEnd = e.currentTarget.selectionStart === value.length;
            if (e.key === "Tab" || atEnd) {
              e.preventDefault();
              acceptGhost();
            }
          } else if (e.key === "Escape") {
            setOpen(false);
            e.currentTarget.blur();
          }
        }}
        placeholder="Search vendors or invoice IDs…"
        className={`relative w-full rounded-lg border bg-transparent pl-10 pr-9 py-2 text-sm transition focus:border-brand-lime focus:shadow-glow focus:outline-none ${
          dark
            ? "border-slate-700 text-slate-100 placeholder:text-slate-500"
            : "border-slate-200"
        }`}
      />

      {value && (
        <button
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => {
            onChange("");
            inputRef.current?.focus();
          }}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          aria-label="Clear search"
        >
          ✕
        </button>
      )}

      {showDropdown && (
        <div className="absolute z-30 mt-1 w-full overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
          {vendorMatches.length > 0 && (
            <div className="px-3 pb-1 pt-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Vendors
            </div>
          )}
          {vendorMatches.map((v) => (
            <button
              key={v}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(v);
                setOpen(false);
              }}
              className="flex w-full items-center justify-between px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-lime-50"
            >
              <span className="flex items-center gap-2">
                <Building2 className="h-3.5 w-3.5 text-brand-limedark" />
                {v}
              </span>
              <span className="text-xs text-slate-400">
                {all.filter((i) => i.vendor_name === v).length}
              </span>
            </button>
          ))}

          {idMatches.length > 0 && (
            <div className="px-3 pb-1 pt-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Invoice IDs
            </div>
          )}
          {idMatches.map((i) => (
            <button
              key={i.id}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(i.invoice_number ?? String(i.id));
                setOpen(false);
              }}
              className="flex w-full items-center justify-between px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-lime-50"
            >
              <span className="flex items-center gap-2">
                <Hash className="h-3.5 w-3.5 text-slate-400" />
                {i.invoice_number ?? i.id}
              </span>
              <span className="truncate pl-2 text-xs text-slate-400">{i.vendor_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
