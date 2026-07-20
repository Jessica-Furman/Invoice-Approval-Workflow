/* @ds-bundle: {"format":4,"namespace":"UpboundGroupDesignSystem_ca0950","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"Checkbox","sourcePath":"components/core/Checkbox.jsx"},{"name":"Dialog","sourcePath":"components/core/Dialog.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"IconButton","sourcePath":"components/core/IconButton.jsx"},{"name":"Input","sourcePath":"components/core/Input.jsx"},{"name":"Radio","sourcePath":"components/core/Radio.jsx"},{"name":"RadioGroup","sourcePath":"components/core/Radio.jsx"},{"name":"Select","sourcePath":"components/core/Select.jsx"},{"name":"Switch","sourcePath":"components/core/Switch.jsx"},{"name":"Tabs","sourcePath":"components/core/Tabs.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"Textarea","sourcePath":"components/core/Textarea.jsx"},{"name":"Toast","sourcePath":"components/core/Toast.jsx"},{"name":"Tooltip","sourcePath":"components/core/Tooltip.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"4565c99bdc55","components/core/Button.jsx":"69c6dacba3c3","components/core/Card.jsx":"5f985bb50790","components/core/Checkbox.jsx":"ceda52f522a6","components/core/Dialog.jsx":"bee7093243db","components/core/Icon.jsx":"fd427949a0cc","components/core/IconButton.jsx":"680b39a8a5cc","components/core/Input.jsx":"a0f75d84597d","components/core/Radio.jsx":"99052bdc1db8","components/core/Select.jsx":"cc3b69da2009","components/core/Switch.jsx":"4302676499d9","components/core/Tabs.jsx":"c7489e17d7b5","components/core/Tag.jsx":"c595b599d6ed","components/core/Textarea.jsx":"cabe0209556a","components/core/Toast.jsx":"b005135e559a","components/core/Tooltip.jsx":"8ce3569b89f2","ui_kits/marketing/Chrome.jsx":"cc504673495b","ui_kits/marketing/HomeView.jsx":"a0bd3f3134a0","ui_kits/marketing/InvestorsView.jsx":"9ad035e15f57","ui_kits/marketing/SolutionsView.jsx":"786e65b36087"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.UpboundGroupDesignSystem_ca0950 = window.UpboundGroupDesignSystem_ca0950 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Badge — small status/count marker.
 * tone: neutral | accent (green) | success | warning | danger | info
 */
function Badge({
  tone = "neutral",
  children,
  style,
  ...rest
}) {
  const tones = {
    neutral: {
      background: "var(--surface-sunken)",
      color: "var(--text-body)"
    },
    accent: {
      background: "var(--up-green)",
      color: "var(--up-near-black)"
    },
    success: {
      background: "rgba(62,155,79,0.14)",
      color: "#2E7C3E"
    },
    warning: {
      background: "rgba(201,138,22,0.16)",
      color: "#966410"
    },
    danger: {
      background: "rgba(198,69,59,0.14)",
      color: "#A5372E"
    },
    info: {
      background: "rgba(62,111,176,0.14)",
      color: "#325C93"
    }
  }[tone];
  return /*#__PURE__*/React.createElement("span", _extends({
    className: `up-badge up-badge--${tone}`,
    style: {
      display: "inline-flex",
      alignItems: "center",
      fontFamily: "var(--font-body)",
      fontSize: 12,
      fontWeight: 600,
      lineHeight: 1,
      padding: "5px 9px",
      borderRadius: "var(--radius-xs)",
      ...tones,
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Button — the primary action element.
 * variant: primary (green, near-black text) · secondary (dark) · outline · ghost
 * One primary (green) CTA per view.
 */
function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  disabled = false,
  iconLeft = null,
  iconRight = null,
  children,
  style,
  ...rest
}) {
  const sizes = {
    sm: {
      fontSize: 14,
      padding: "8px 16px",
      gap: 6,
      minHeight: 36
    },
    md: {
      fontSize: 15,
      padding: "11px 22px",
      gap: 8,
      minHeight: 44
    },
    lg: {
      fontSize: 16,
      padding: "14px 28px",
      gap: 10,
      minHeight: 52
    }
  }[size];
  const variants = {
    primary: {
      background: "var(--up-green)",
      color: "var(--up-near-black)",
      border: "1px solid transparent"
    },
    secondary: {
      background: "var(--up-near-black)",
      color: "var(--up-off-white)",
      border: "1px solid transparent"
    },
    outline: {
      background: "transparent",
      color: "var(--text-strong)",
      border: "1px solid var(--border-strong)"
    },
    ghost: {
      background: "transparent",
      color: "var(--text-strong)",
      border: "1px solid transparent"
    }
  }[variant];
  return /*#__PURE__*/React.createElement("button", _extends({
    disabled: disabled,
    className: `up-btn up-btn--${variant}`,
    style: {
      fontFamily: "var(--font-body)",
      fontWeight: 600,
      letterSpacing: "0.005em",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      width: fullWidth ? "100%" : "auto",
      borderRadius: "var(--radius-pill)",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.45 : 1,
      transition: "background var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out)",
      whiteSpace: "nowrap",
      ...sizes,
      ...variants,
      ...style
    },
    onMouseDown: e => {
      if (!disabled) e.currentTarget.style.transform = "scale(0.98)";
    },
    onMouseUp: e => {
      e.currentTarget.style.transform = "scale(1)";
    },
    onMouseLeave: e => {
      e.currentTarget.style.transform = "scale(1)";
    }
  }, rest), iconLeft, children, iconRight);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Card — flat surface with hairline border + soft single-layer shadow.
 * No colored left-borders. Optional hover lift for interactive cards.
 */
function Card({
  interactive = false,
  padding = 24,
  children,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", _extends({
    className: "up-card",
    onMouseEnter: () => interactive && setHover(true),
    onMouseLeave: () => interactive && setHover(false),
    style: {
      background: "var(--surface-card)",
      border: "1px solid var(--border-subtle)",
      borderRadius: "var(--radius-lg)",
      boxShadow: hover ? "var(--shadow-md)" : "var(--shadow-sm)",
      padding,
      transition: "box-shadow var(--dur-base) var(--ease-out), transform var(--dur-base) var(--ease-out)",
      transform: hover ? "translateY(-2px)" : "translateY(0)",
      cursor: interactive ? "pointer" : "default",
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/core/Checkbox.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Checkbox — green-filled when checked, near-black check.
 */
function Checkbox({
  label,
  checked,
  defaultChecked,
  onChange,
  disabled,
  id,
  style,
  ...rest
}) {
  const inputId = id || React.useId();
  const isControlled = checked !== undefined;
  const [internal, setInternal] = React.useState(defaultChecked || false);
  const on = isControlled ? checked : internal;
  return /*#__PURE__*/React.createElement("label", {
    htmlFor: inputId,
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      fontFamily: "var(--font-body)",
      fontSize: 15,
      color: "var(--text-body)",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.5 : 1,
      ...style
    }
  }, /*#__PURE__*/React.createElement("input", _extends({
    id: inputId,
    type: "checkbox",
    checked: on,
    disabled: disabled,
    onChange: e => {
      if (!isControlled) setInternal(e.target.checked);
      onChange && onChange(e);
    },
    style: {
      position: "absolute",
      opacity: 0,
      width: 0,
      height: 0
    }
  }, rest)), /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      width: 20,
      height: 20,
      flex: "none",
      borderRadius: "var(--radius-xs)",
      border: on ? "1px solid transparent" : "1px solid var(--border-strong)",
      background: on ? "var(--up-green)" : "var(--surface-card)",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      transition: "background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out)"
    }
  }, on && /*#__PURE__*/React.createElement("svg", {
    width: "12",
    height: "12",
    viewBox: "0 0 12 12",
    fill: "none"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M2.5 6.5L5 9L9.5 3.5",
    stroke: "#1A1A1A",
    strokeWidth: "1.9",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }))), label);
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/core/Dialog.jsx
try { (() => {
/**
 * Dialog — centered modal over a dimmed navy scrim.
 */
function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
  width = 480,
  style
}) {
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    onClick: onClose,
    style: {
      position: "fixed",
      inset: 0,
      zIndex: 1000,
      background: "rgba(26,26,26,0.55)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: 24,
      animation: "upFade var(--dur-base) var(--ease-out)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    role: "dialog",
    "aria-modal": "true",
    onClick: e => e.stopPropagation(),
    style: {
      width,
      maxWidth: "100%",
      background: "var(--surface-card)",
      borderRadius: "var(--radius-lg)",
      boxShadow: "var(--shadow-lg)",
      padding: 28,
      fontFamily: "var(--font-body)",
      animation: "upRise var(--dur-slow) var(--ease-out)",
      ...style
    }
  }, title && /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "flex-start",
      justifyContent: "space-between",
      gap: 16,
      marginBottom: 12
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 600,
      fontSize: 22,
      color: "var(--text-strong)",
      margin: 0
    }
  }, title), /*#__PURE__*/React.createElement("button", {
    "aria-label": "Close",
    onClick: onClose,
    style: {
      border: 0,
      background: "transparent",
      cursor: "pointer",
      fontSize: 22,
      lineHeight: 1,
      color: "var(--text-muted)"
    }
  }, "\xD7")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 15,
      color: "var(--text-body)",
      lineHeight: 1.5
    }
  }, children), footer && /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 12,
      justifyContent: "flex-end",
      marginTop: 24
    }
  }, footer)), /*#__PURE__*/React.createElement("style", null, `
        @keyframes upFade { from { opacity: 0 } to { opacity: 1 } }
        @keyframes upRise { from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: translateY(0) } }
      `));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/core/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useEffect,
  useRef
} = React;
/**
 * Icon — single-weight, monochrome line icon (Lucide substitute set).
 * Renders currentColor so it inherits text color. Reserve green for at most
 * one icon per view. Requires the Lucide CDN script on the page:
 *   <script src="https://unpkg.com/lucide@latest"></script>
 */
function Icon({
  name,
  size = 20,
  strokeWidth = 1.75,
  color,
  style,
  className = "",
  ...rest
}) {
  const ref = useRef(null);
  useEffect(() => {
    if (window.lucide && ref.current) {
      // Re-render just this node's icon
      window.lucide.createIcons({
        icons: window.lucide.icons,
        attrs: {
          "stroke-width": strokeWidth
        },
        nameAttr: "data-lucide"
      });
    }
  }, [name, strokeWidth]);
  return /*#__PURE__*/React.createElement("i", _extends({
    ref: ref,
    "data-lucide": name,
    className: `up-icon ${className}`,
    style: {
      display: "inline-flex",
      width: size,
      height: size,
      color: color || "inherit",
      verticalAlign: "middle",
      ...style
    }
  }, rest));
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/core/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * IconButton — a square/round button holding a single icon.
 * variant: primary | secondary | outline | ghost · matches Button.
 */
function IconButton({
  icon,
  name,
  variant = "ghost",
  size = "md",
  round = false,
  disabled = false,
  "aria-label": ariaLabel,
  style,
  ...rest
}) {
  const dims = {
    sm: 36,
    md: 44,
    lg: 52
  }[size];
  const iconSize = {
    sm: 18,
    md: 20,
    lg: 24
  }[size];
  const variants = {
    primary: {
      background: "var(--up-green)",
      color: "var(--up-near-black)",
      border: "1px solid transparent"
    },
    secondary: {
      background: "var(--up-near-black)",
      color: "var(--up-off-white)",
      border: "1px solid transparent"
    },
    outline: {
      background: "transparent",
      color: "var(--text-strong)",
      border: "1px solid var(--border-strong)"
    },
    ghost: {
      background: "transparent",
      color: "var(--text-strong)",
      border: "1px solid transparent"
    }
  }[variant];
  return /*#__PURE__*/React.createElement("button", _extends({
    "aria-label": ariaLabel,
    disabled: disabled,
    className: `up-iconbtn up-iconbtn--${variant}`,
    style: {
      width: dims,
      height: dims,
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      borderRadius: round ? "var(--radius-pill)" : "var(--radius-sm)",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.45 : 1,
      transition: "background var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out)",
      ...variants,
      ...style
    },
    onMouseDown: e => {
      if (!disabled) e.currentTarget.style.transform = "scale(0.94)";
    },
    onMouseUp: e => {
      e.currentTarget.style.transform = "scale(1)";
    },
    onMouseLeave: e => {
      e.currentTarget.style.transform = "scale(1)";
    }
  }, rest), icon || /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: name,
    size: iconSize
  }));
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/core/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Input — single-line text field with label, hint, and error states.
 * Focus shows the green ring.
 */
function Input({
  label,
  hint,
  error,
  id,
  iconLeft,
  style,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const inputId = id || React.useId();
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 6,
      fontFamily: "var(--font-body)"
    }
  }, label && /*#__PURE__*/React.createElement("label", {
    htmlFor: inputId,
    style: {
      fontSize: 13,
      fontWeight: 600,
      color: "var(--text-strong)"
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative",
      display: "flex",
      alignItems: "center"
    }
  }, iconLeft && /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      left: 12,
      display: "inline-flex",
      color: "var(--text-muted)",
      pointerEvents: "none"
    }
  }, iconLeft), /*#__PURE__*/React.createElement("input", _extends({
    id: inputId,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      width: "100%",
      boxSizing: "border-box",
      fontFamily: "var(--font-body)",
      fontSize: 15,
      color: "var(--text-strong)",
      background: "var(--surface-card)",
      padding: iconLeft ? "11px 14px 11px 38px" : "11px 14px",
      borderRadius: "var(--radius-sm)",
      border: `1px solid ${error ? "var(--status-danger)" : focus ? "var(--up-near-black)" : "var(--border-default)"}`,
      boxShadow: focus && !error ? "var(--shadow-focus)" : "none",
      outline: "none",
      transition: "border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out)",
      ...style
    }
  }, rest))), (hint || error) && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: error ? "var(--status-danger)" : "var(--text-muted)"
    }
  }, error || hint));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Input.jsx", error: String((e && e.message) || e) }); }

// components/core/Radio.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Radio — single choice within a RadioGroup (or standalone).
 */
function Radio({
  label,
  checked,
  name,
  value,
  onChange,
  disabled,
  id,
  style,
  ...rest
}) {
  const inputId = id || React.useId();
  return /*#__PURE__*/React.createElement("label", {
    htmlFor: inputId,
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      fontFamily: "var(--font-body)",
      fontSize: 15,
      color: "var(--text-body)",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.5 : 1,
      ...style
    }
  }, /*#__PURE__*/React.createElement("input", _extends({
    id: inputId,
    type: "radio",
    name: name,
    value: value,
    checked: checked,
    disabled: disabled,
    onChange: onChange,
    style: {
      position: "absolute",
      opacity: 0,
      width: 0,
      height: 0
    }
  }, rest)), /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      width: 20,
      height: 20,
      flex: "none",
      borderRadius: "var(--radius-dot)",
      border: checked ? "6px solid var(--up-near-black)" : "1px solid var(--border-strong)",
      background: checked ? "var(--up-green)" : "var(--surface-card)",
      boxSizing: "border-box",
      transition: "border-color var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out)"
    }
  }), label);
}

/**
 * RadioGroup — manages a set of Radios by value.
 */
function RadioGroup({
  name,
  value,
  onChange,
  options = [],
  style
}) {
  const groupName = name || React.useId();
  return /*#__PURE__*/React.createElement("div", {
    role: "radiogroup",
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 10,
      ...style
    }
  }, options.map(o => {
    const val = o.value ?? o;
    return /*#__PURE__*/React.createElement(Radio, {
      key: val,
      name: groupName,
      value: val,
      label: o.label ?? o,
      checked: value === val,
      onChange: () => onChange && onChange(val)
    });
  }));
}
Object.assign(__ds_scope, { Radio, RadioGroup });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Radio.jsx", error: String((e && e.message) || e) }); }

// components/core/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Select — styled native select with label and hint.
 */
function Select({
  label,
  hint,
  error,
  id,
  options = [],
  children,
  style,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const inputId = id || React.useId();
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 6,
      fontFamily: "var(--font-body)"
    }
  }, label && /*#__PURE__*/React.createElement("label", {
    htmlFor: inputId,
    style: {
      fontSize: 13,
      fontWeight: 600,
      color: "var(--text-strong)"
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative"
    }
  }, /*#__PURE__*/React.createElement("select", _extends({
    id: inputId,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      width: "100%",
      boxSizing: "border-box",
      appearance: "none",
      fontFamily: "var(--font-body)",
      fontSize: 15,
      color: "var(--text-strong)",
      background: "var(--surface-card)",
      padding: "11px 38px 11px 14px",
      borderRadius: "var(--radius-sm)",
      border: `1px solid ${error ? "var(--status-danger)" : focus ? "var(--up-near-black)" : "var(--border-default)"}`,
      boxShadow: focus && !error ? "var(--shadow-focus)" : "none",
      outline: "none",
      cursor: "pointer",
      transition: "border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out)",
      ...style
    }
  }, rest), options.length ? options.map(o => /*#__PURE__*/React.createElement("option", {
    key: o.value ?? o,
    value: o.value ?? o
  }, o.label ?? o)) : children), /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      right: 14,
      top: "50%",
      transform: "translateY(-50%)",
      pointerEvents: "none",
      color: "var(--text-muted)",
      fontSize: 12
    }
  }, "\u25BE")), (hint || error) && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: error ? "var(--status-danger)" : "var(--text-muted)"
    }
  }, error || hint));
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Select.jsx", error: String((e && e.message) || e) }); }

// components/core/Switch.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Switch — on/off toggle. Green track when on.
 */
function Switch({
  checked,
  defaultChecked,
  onChange,
  disabled,
  label,
  id,
  style,
  ...rest
}) {
  const inputId = id || React.useId();
  const isControlled = checked !== undefined;
  const [internal, setInternal] = React.useState(defaultChecked || false);
  const on = isControlled ? checked : internal;
  return /*#__PURE__*/React.createElement("label", {
    htmlFor: inputId,
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      fontFamily: "var(--font-body)",
      fontSize: 15,
      color: "var(--text-body)",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.5 : 1,
      ...style
    }
  }, /*#__PURE__*/React.createElement("input", _extends({
    id: inputId,
    type: "checkbox",
    role: "switch",
    checked: on,
    disabled: disabled,
    onChange: e => {
      if (!isControlled) setInternal(e.target.checked);
      onChange && onChange(e);
    },
    style: {
      position: "absolute",
      opacity: 0,
      width: 0,
      height: 0
    }
  }, rest)), /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      width: 44,
      height: 26,
      flex: "none",
      borderRadius: "var(--radius-pill)",
      background: on ? "var(--up-green)" : "var(--border-strong)",
      position: "relative",
      transition: "background var(--dur-base) var(--ease-out)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      top: 3,
      left: on ? 21 : 3,
      width: 20,
      height: 20,
      borderRadius: "var(--radius-dot)",
      background: on ? "var(--up-near-black)" : "var(--up-white)",
      boxShadow: "var(--shadow-xs)",
      transition: "left var(--dur-base) var(--ease-out), background var(--dur-base) var(--ease-out)"
    }
  })), label);
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Switch.jsx", error: String((e && e.message) || e) }); }

// components/core/Tabs.jsx
try { (() => {
/**
 * Tabs — underline tab set. Active tab underlined in green.
 */
function Tabs({
  tabs = [],
  value,
  defaultValue,
  onChange,
  style
}) {
  const isControlled = value !== undefined;
  const [internal, setInternal] = React.useState(defaultValue ?? (tabs[0] && (tabs[0].value ?? tabs[0])));
  const active = isControlled ? value : internal;
  return /*#__PURE__*/React.createElement("div", {
    role: "tablist",
    style: {
      display: "flex",
      gap: 28,
      borderBottom: "1px solid var(--border-subtle)",
      ...style
    }
  }, tabs.map(t => {
    const val = t.value ?? t;
    const label = t.label ?? t;
    const on = active === val;
    return /*#__PURE__*/React.createElement("button", {
      key: val,
      role: "tab",
      "aria-selected": on,
      onClick: () => {
        if (!isControlled) setInternal(val);
        onChange && onChange(val);
      },
      style: {
        border: 0,
        background: "transparent",
        cursor: "pointer",
        fontFamily: "var(--font-body)",
        fontSize: 15,
        fontWeight: on ? 600 : 500,
        color: on ? "var(--text-strong)" : "var(--text-muted)",
        padding: "0 0 12px",
        position: "relative",
        transition: "color var(--dur-fast) var(--ease-out)"
      }
    }, label, /*#__PURE__*/React.createElement("span", {
      style: {
        position: "absolute",
        left: 0,
        right: 0,
        bottom: -1,
        height: 2,
        background: on ? "var(--up-green)" : "transparent",
        borderRadius: "var(--radius-pill)",
        transition: "background var(--dur-fast) var(--ease-out)"
      }
    }));
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Tag — pill-shaped label/chip, optionally removable.
 * selected raises it to the green accent state.
 */
function Tag({
  selected = false,
  onRemove,
  children,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("span", _extends({
    className: "up-tag",
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      fontFamily: "var(--font-body)",
      fontSize: 13,
      fontWeight: 500,
      lineHeight: 1,
      padding: "7px 12px",
      borderRadius: "var(--radius-pill)",
      border: selected ? "1px solid transparent" : "1px solid var(--border-default)",
      background: selected ? "var(--up-green)" : "transparent",
      color: selected ? "var(--up-near-black)" : "var(--text-body)",
      transition: "background var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out)",
      ...style
    }
  }, rest), children, onRemove && /*#__PURE__*/React.createElement("button", {
    "aria-label": "Remove",
    onClick: onRemove,
    style: {
      border: 0,
      background: "transparent",
      cursor: "pointer",
      color: "inherit",
      opacity: 0.6,
      padding: 0,
      display: "inline-flex",
      fontSize: 14,
      lineHeight: 1
    }
  }, "\xD7"));
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/core/Textarea.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Textarea — multi-line text field. Same visual language as Input.
 */
function Textarea({
  label,
  hint,
  error,
  id,
  rows = 4,
  style,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const inputId = id || React.useId();
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 6,
      fontFamily: "var(--font-body)"
    }
  }, label && /*#__PURE__*/React.createElement("label", {
    htmlFor: inputId,
    style: {
      fontSize: 13,
      fontWeight: 600,
      color: "var(--text-strong)"
    }
  }, label), /*#__PURE__*/React.createElement("textarea", _extends({
    id: inputId,
    rows: rows,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      width: "100%",
      boxSizing: "border-box",
      fontFamily: "var(--font-body)",
      fontSize: 15,
      lineHeight: 1.5,
      color: "var(--text-strong)",
      background: "var(--surface-card)",
      padding: "11px 14px",
      borderRadius: "var(--radius-sm)",
      border: `1px solid ${error ? "var(--status-danger)" : focus ? "var(--up-near-black)" : "var(--border-default)"}`,
      boxShadow: focus && !error ? "var(--shadow-focus)" : "none",
      outline: "none",
      resize: "vertical",
      transition: "border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out)",
      ...style
    }
  }, rest)), (hint || error) && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: error ? "var(--status-danger)" : "var(--text-muted)"
    }
  }, error || hint));
}
Object.assign(__ds_scope, { Textarea });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Textarea.jsx", error: String((e && e.message) || e) }); }

// components/core/Toast.jsx
try { (() => {
/**
 * Toast — transient notification. Dark surface, optional green accent bar.
 * tone: neutral | success | warning | danger
 */
function Toast({
  tone = "neutral",
  title,
  children,
  onClose,
  style
}) {
  const accent = {
    neutral: "var(--up-green)",
    success: "var(--status-success)",
    warning: "var(--status-warning)",
    danger: "var(--status-danger)"
  }[tone];
  return /*#__PURE__*/React.createElement("div", {
    role: "status",
    style: {
      display: "flex",
      alignItems: "flex-start",
      gap: 12,
      background: "var(--up-near-black)",
      color: "var(--up-off-white)",
      borderRadius: "var(--radius-md)",
      boxShadow: "var(--shadow-lg)",
      padding: "14px 16px",
      minWidth: 280,
      maxWidth: 420,
      fontFamily: "var(--font-body)",
      position: "relative",
      overflow: "hidden",
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      left: 0,
      top: 0,
      bottom: 0,
      width: 4,
      background: accent
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      paddingLeft: 4
    }
  }, title && /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 600,
      fontSize: 14,
      marginBottom: children ? 2 : 0
    }
  }, title), children && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: "var(--up-cool-grey)",
      lineHeight: 1.4
    }
  }, children)), onClose && /*#__PURE__*/React.createElement("button", {
    "aria-label": "Dismiss",
    onClick: onClose,
    style: {
      border: 0,
      background: "transparent",
      cursor: "pointer",
      color: "var(--up-cool-grey)",
      fontSize: 18,
      lineHeight: 1
    }
  }, "\xD7"));
}
Object.assign(__ds_scope, { Toast });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Toast.jsx", error: String((e && e.message) || e) }); }

// components/core/Tooltip.jsx
try { (() => {
/**
 * Tooltip — hover/focus label on a near-black surface.
 */
function Tooltip({
  label,
  side = "top",
  children,
  style
}) {
  const [show, setShow] = React.useState(false);
  const pos = {
    top: {
      bottom: "calc(100% + 8px)",
      left: "50%",
      transform: "translateX(-50%)"
    },
    bottom: {
      top: "calc(100% + 8px)",
      left: "50%",
      transform: "translateX(-50%)"
    },
    left: {
      right: "calc(100% + 8px)",
      top: "50%",
      transform: "translateY(-50%)"
    },
    right: {
      left: "calc(100% + 8px)",
      top: "50%",
      transform: "translateY(-50%)"
    }
  }[side];
  return /*#__PURE__*/React.createElement("span", {
    style: {
      position: "relative",
      display: "inline-flex"
    },
    onMouseEnter: () => setShow(true),
    onMouseLeave: () => setShow(false),
    onFocus: () => setShow(true),
    onBlur: () => setShow(false)
  }, children, show && /*#__PURE__*/React.createElement("span", {
    role: "tooltip",
    style: {
      position: "absolute",
      zIndex: 100,
      ...pos,
      background: "var(--up-near-black)",
      color: "var(--up-off-white)",
      fontFamily: "var(--font-body)",
      fontSize: 12,
      fontWeight: 500,
      padding: "6px 10px",
      borderRadius: "var(--radius-xs)",
      whiteSpace: "nowrap",
      pointerEvents: "none",
      boxShadow: "var(--shadow-md)",
      animation: "upTipIn var(--dur-fast) var(--ease-out)",
      ...style
    }
  }, label), /*#__PURE__*/React.createElement("style", null, `@keyframes upTipIn { from { opacity: 0 } to { opacity: 1 } }`));
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tooltip.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/Chrome.jsx
try { (() => {
// Shared chrome for the Upbound marketing site: Wordmark, Header, Footer.
// Composes the design-system bundle (window.UpboundGroupDesignSystem_ca0950).
const _NS = window.UpboundGroupDesignSystem_ca0950;
const {
  Button: CButton,
  IconButton: CIconButton,
  Icon: CIcon
} = _NS;
function Wordmark({
  dark = false,
  dot = true,
  size = 24
}) {
  return /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 600,
      fontSize: size,
      letterSpacing: "-0.01em",
      color: dark ? "var(--up-off-white)" : "var(--up-near-black)",
      lineHeight: 1,
      userSelect: "none"
    }
  }, "upbound", dot && /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--up-green)"
    }
  }, "."));
}
const NAV = ["Solutions", "Investors", "Careers", "About"];
function Header({
  route,
  onNavigate,
  onDemo
}) {
  return /*#__PURE__*/React.createElement("header", {
    style: {
      position: "sticky",
      top: 0,
      zIndex: 50,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "16px 40px",
      background: "rgba(53,50,61,0.92)",
      backdropFilter: "blur(8px)",
      borderBottom: "1px solid var(--divider-on-dark)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 44
    }
  }, /*#__PURE__*/React.createElement("a", {
    onClick: () => onNavigate("home"),
    style: {
      cursor: "pointer",
      textDecoration: "none"
    }
  }, /*#__PURE__*/React.createElement(Wordmark, {
    dark: true
  })), /*#__PURE__*/React.createElement("nav", {
    style: {
      display: "flex",
      gap: 28
    }
  }, NAV.map(item => {
    const key = item.toLowerCase();
    const active = route === key;
    return /*#__PURE__*/React.createElement("a", {
      key: item,
      onClick: () => onNavigate(key),
      style: {
        cursor: "pointer",
        textDecoration: "none",
        fontFamily: "var(--font-body)",
        fontSize: 14,
        fontWeight: 500,
        color: active ? "var(--up-off-white)" : "var(--up-cool-grey)",
        transition: "color var(--dur-fast) var(--ease-out)"
      }
    }, item);
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 14
    }
  }, /*#__PURE__*/React.createElement("a", {
    onClick: () => onNavigate("signin"),
    style: {
      cursor: "pointer",
      textDecoration: "none",
      fontFamily: "var(--font-body)",
      fontSize: 14,
      fontWeight: 500,
      color: "var(--up-cool-grey)"
    }
  }, "Sign in"), /*#__PURE__*/React.createElement(CButton, {
    variant: "primary",
    size: "sm",
    onClick: onDemo,
    iconRight: /*#__PURE__*/React.createElement(CIcon, {
      name: "arrow-up-right",
      size: 16
    })
  }, "Request a demo")));
}
function Footer({
  onNavigate
}) {
  const cols = [{
    h: "Solutions",
    items: ["Lending", "Payments", "Marketplace", "Analytics"]
  }, {
    h: "Company",
    items: ["About", "Investors", "Careers", "Newsroom"]
  }, {
    h: "Resources",
    items: ["Insights", "Help center", "Security", "Contact"]
  }];
  return /*#__PURE__*/React.createElement("footer", {
    style: {
      background: "var(--up-near-black)",
      color: "var(--up-off-white)",
      padding: "56px 40px 32px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto",
      display: "grid",
      gridTemplateColumns: "1.4fr 1fr 1fr 1fr",
      gap: 40
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Wordmark, {
    dark: true
  }), /*#__PURE__*/React.createElement("p", {
    style: {
      marginTop: 16,
      maxWidth: 240,
      fontSize: 14,
      color: "var(--up-cool-grey)",
      lineHeight: 1.5
    }
  }, "We exist to elevate financial opportunity for all.")), cols.map(c => /*#__PURE__*/React.createElement("div", {
    key: c.h
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: "0.12em",
      textTransform: "uppercase",
      color: "var(--up-cool-grey)",
      marginBottom: 16
    }
  }, c.h), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, c.items.map(i => /*#__PURE__*/React.createElement("a", {
    key: i,
    style: {
      cursor: "pointer",
      textDecoration: "none",
      fontSize: 14,
      color: "var(--up-off-white)",
      opacity: 0.85
    }
  }, i)))))), /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "40px auto 0",
      paddingTop: 24,
      borderTop: "1px solid var(--divider-on-dark)",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      fontSize: 13,
      color: "var(--up-cool-grey)"
    }
  }, /*#__PURE__*/React.createElement("span", null, "\xA9 2026 Upbound Group. All rights reserved."), /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      gap: 20
    }
  }, /*#__PURE__*/React.createElement("a", {
    style: {
      cursor: "pointer",
      color: "inherit",
      textDecoration: "none"
    }
  }, "Privacy"), /*#__PURE__*/React.createElement("a", {
    style: {
      cursor: "pointer",
      color: "inherit",
      textDecoration: "none"
    }
  }, "Terms"))));
}
Object.assign(window, {
  Wordmark,
  Header,
  Footer,
  MKT_NAV: NAV
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/Chrome.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/HomeView.jsx
try { (() => {
// Home / landing view for the Upbound marketing site.
const _NSH = window.UpboundGroupDesignSystem_ca0950;
const {
  Button: HButton,
  Icon: HIcon,
  Card: HCard,
  Badge: HBadge
} = _NSH;
function Hero({
  onDemo,
  onNavigate
}) {
  return /*#__PURE__*/React.createElement("section", {
    style: {
      position: "relative",
      background: "var(--up-navy)",
      overflow: "hidden",
      padding: "96px 40px 108px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      inset: "0 -30% 0 58%",
      background: "var(--up-charcoal)",
      transform: "skewX(-30deg)",
      transformOrigin: "bottom left",
      opacity: 0.7
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative",
      maxWidth: 1120,
      margin: "0 auto",
      display: "grid",
      gridTemplateColumns: "1.15fr 0.85fr",
      gap: 48,
      alignItems: "center"
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: "0.12em",
      textTransform: "uppercase",
      color: "var(--up-green)",
      marginBottom: 20
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: "50%",
      background: "var(--up-green)"
    }
  }), " Financial opportunity, elevated"), /*#__PURE__*/React.createElement("h1", {
    style: {
      color: "var(--up-off-white)",
      fontSize: 60,
      lineHeight: 1.02,
      letterSpacing: "-0.02em",
      maxWidth: 620
    }
  }, "We help people move their finances forward."), /*#__PURE__*/React.createElement("p", {
    style: {
      marginTop: 22,
      maxWidth: 470,
      fontSize: 18,
      lineHeight: 1.5,
      color: "var(--up-cool-grey)"
    }
  }, "Upbound Group builds the lending, payments, and marketplace platforms that open real financial opportunity \u2014 for enterprises and the people they serve."), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 14,
      marginTop: 32
    }
  }, /*#__PURE__*/React.createElement(HButton, {
    variant: "primary",
    size: "lg",
    onClick: onDemo,
    iconRight: /*#__PURE__*/React.createElement(HIcon, {
      name: "arrow-up-right",
      size: 20
    })
  }, "Request a demo"), /*#__PURE__*/React.createElement(HButton, {
    variant: "outline",
    size: "lg",
    onClick: () => onNavigate("solutions"),
    style: {
      color: "var(--up-off-white)",
      borderColor: "var(--up-cool-grey)"
    }
  }, "Explore solutions"))), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative"
    }
  }, /*#__PURE__*/React.createElement(HCard, {
    style: {
      background: "var(--up-charcoal)",
      border: "1px solid var(--divider-on-dark)",
      padding: 26
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      fontWeight: 700,
      letterSpacing: "0.12em",
      textTransform: "uppercase",
      color: "var(--up-cool-grey)"
    }
  }, "Assets enabled"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 700,
      fontSize: 46,
      color: "var(--up-off-white)",
      marginTop: 6,
      lineHeight: 1
    }
  }, "$4.2B", /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--up-green)"
    }
  }, ".")), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 1,
      background: "var(--divider-on-dark)",
      margin: "20px 0"
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 14
    }
  }, [["Approval rate", "92%"], ["Avg. time to fund", "48 hrs"], ["Partner NPS", "71"]].map(([k, v]) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 14,
      color: "var(--up-cool-grey)"
    }
  }, k), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 600,
      fontSize: 18,
      color: "var(--up-off-white)"
    }
  }, v))))))));
}
function LogoStrip() {
  const names = ["Meridian", "Northwind", "Cedar Bank", "Vantage", "Halcyon"];
  return /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-card)",
      padding: "28px 40px",
      borderBottom: "1px solid var(--border-subtle)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 24,
      flexWrap: "wrap"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      color: "var(--text-muted)"
    }
  }, "Trusted by forward-looking finance teams"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 36,
      alignItems: "center"
    }
  }, names.map(n => /*#__PURE__*/React.createElement("span", {
    key: n,
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 600,
      fontSize: 17,
      color: "var(--text-muted)",
      opacity: 0.7
    }
  }, n)))));
}
const SOLUTIONS = [{
  icon: "landmark",
  title: "Lending",
  body: "Underwrite, approve, and fund in days — not weeks — with transparent terms."
}, {
  icon: "credit-card",
  title: "Payments",
  body: "Move money reliably across partners with real-time settlement and controls."
}, {
  icon: "store",
  title: "Marketplace",
  body: "Connect merchants and customers with flexible, opportunity-first financing."
}, {
  icon: "line-chart",
  title: "Analytics",
  body: "See the whole portfolio clearly and act on what moves outcomes upward."
}];
function SolutionsGrid({
  onNavigate
}) {
  return /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-page)",
      padding: "80px 40px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 620,
      marginBottom: 44
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: "0.12em",
      textTransform: "uppercase",
      color: "var(--text-muted)",
      marginBottom: 14
    }
  }, "What we build"), /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 36
    }
  }, "One platform for the whole financial relationship.")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(2, 1fr)",
      gap: 20
    }
  }, SOLUTIONS.map(s => /*#__PURE__*/React.createElement(HCard, {
    key: s.title,
    interactive: true,
    onClick: () => onNavigate("solutions"),
    padding: 28
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 44,
      height: 44,
      borderRadius: "var(--radius-md)",
      background: "var(--up-navy)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 18
    }
  }, /*#__PURE__*/React.createElement(HIcon, {
    name: s.icon,
    size: 22,
    color: "var(--up-green)"
  })), /*#__PURE__*/React.createElement("h3", {
    style: {
      fontSize: 20,
      marginBottom: 8
    }
  }, s.title), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 15,
      color: "var(--text-muted)",
      lineHeight: 1.5,
      margin: 0
    }
  }, s.body))))));
}
function StatBand() {
  const stats = [["1994", "Founded"], ["$4.2B", "Assets enabled"], ["3.1M", "People served"], ["18", "Markets"]];
  return /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--up-near-black)",
      padding: "64px 40px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto",
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 24
    }
  }, stats.map(([v, k], i) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      borderLeft: i === 0 ? "none" : "1px solid var(--divider-on-dark)",
      paddingLeft: i === 0 ? 0 : 24
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 700,
      fontSize: 42,
      color: "var(--up-off-white)",
      lineHeight: 1
    }
  }, v), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: "var(--up-cool-grey)",
      marginTop: 8
    }
  }, k)))));
}
function CtaBand({
  onDemo
}) {
  return /*#__PURE__*/React.createElement("section", {
    style: {
      position: "relative",
      background: "var(--up-navy)",
      padding: "72px 40px",
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      inset: "0 60% 0 -20%",
      background: "var(--up-charcoal)",
      transform: "skewX(-30deg)",
      transformOrigin: "bottom right",
      opacity: 0.6
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative",
      maxWidth: 1120,
      margin: "0 auto",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 32,
      flexWrap: "wrap"
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      color: "var(--up-off-white)",
      fontSize: 34,
      maxWidth: 560
    }
  }, "Ready to move your finances forward?"), /*#__PURE__*/React.createElement(HButton, {
    variant: "primary",
    size: "lg",
    onClick: onDemo,
    iconRight: /*#__PURE__*/React.createElement(HIcon, {
      name: "arrow-up-right",
      size: 20
    })
  }, "Request a demo")));
}
function HomeView({
  onDemo,
  onNavigate
}) {
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Hero, {
    onDemo: onDemo,
    onNavigate: onNavigate
  }), /*#__PURE__*/React.createElement(LogoStrip, null), /*#__PURE__*/React.createElement(SolutionsGrid, {
    onNavigate: onNavigate
  }), /*#__PURE__*/React.createElement(StatBand, null), /*#__PURE__*/React.createElement(CtaBand, {
    onDemo: onDemo
  }));
}
Object.assign(window, {
  HomeView
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/HomeView.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/InvestorsView.jsx
try { (() => {
// Investors & Careers views.
const _NSI = window.UpboundGroupDesignSystem_ca0950;
const {
  Button: IButton,
  Icon: IIcon,
  Card: ICard,
  Badge: IBadge
} = _NSI;
function InvestorsView({
  onDemo
}) {
  const highlights = [["Revenue", "$1.28B", "+11% YoY"], ["Adj. EBITDA", "$214M", "+16% YoY"], ["Free cash flow", "$168M", "+9% YoY"], ["Dividend", "$0.37", "per share"]];
  const events = [["Q2 2026 Earnings Call", "Aug 4, 2026", "Upcoming"], ["Annual Shareholder Meeting", "Jun 12, 2026", "Replay"], ["Investor Day 2026", "Mar 20, 2026", "Replay"]];
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--up-navy)",
      padding: "64px 40px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: "0.12em",
      textTransform: "uppercase",
      color: "var(--up-green)",
      marginBottom: 14
    }
  }, "Investors"), /*#__PURE__*/React.createElement("h1", {
    style: {
      color: "var(--up-off-white)",
      fontSize: 46,
      maxWidth: 640
    }
  }, "Disciplined growth. Grounded ambition."), /*#__PURE__*/React.createElement("p", {
    style: {
      color: "var(--up-cool-grey)",
      marginTop: 18,
      maxWidth: 520,
      fontSize: 17,
      lineHeight: 1.5
    }
  }, "A durable business built to compound financial opportunity \u2014 for our customers and our shareholders."))), /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-card)",
      padding: "48px 40px",
      borderBottom: "1px solid var(--border-subtle)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto",
      display: "grid",
      gridTemplateColumns: "repeat(4, 1fr)",
      gap: 20
    }
  }, highlights.map(([k, v, d]) => /*#__PURE__*/React.createElement("div", {
    key: k
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      fontWeight: 700,
      letterSpacing: "0.1em",
      textTransform: "uppercase",
      color: "var(--text-muted)"
    }
  }, k), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 700,
      fontSize: 38,
      color: "var(--text-strong)",
      marginTop: 8,
      lineHeight: 1
    }
  }, v), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: "var(--status-success)",
      marginTop: 6,
      fontWeight: 600
    }
  }, d))))), /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-page)",
      padding: "72px 40px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto",
      display: "grid",
      gridTemplateColumns: "1.2fr 0.8fr",
      gap: 40
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 30,
      marginBottom: 24
    }
  }, "Events & filings"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 14
    }
  }, events.map(([t, d, s]) => /*#__PURE__*/React.createElement(ICard, {
    key: t,
    interactive: true,
    padding: 20,
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 600,
      fontSize: 17,
      color: "var(--text-strong)"
    }
  }, t), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      color: "var(--text-muted)",
      marginTop: 4
    }
  }, d)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 14
    }
  }, /*#__PURE__*/React.createElement(IBadge, {
    tone: s === "Upcoming" ? "accent" : "neutral"
  }, s), /*#__PURE__*/React.createElement(IIcon, {
    name: "arrow-up-right",
    size: 18,
    color: "var(--text-muted)"
  })))))), /*#__PURE__*/React.createElement(ICard, {
    padding: 26,
    style: {
      background: "var(--up-near-black)"
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      color: "var(--up-off-white)",
      fontSize: 20,
      marginBottom: 10
    }
  }, "Investor resources"), /*#__PURE__*/React.createElement("p", {
    style: {
      color: "var(--up-cool-grey)",
      fontSize: 14,
      lineHeight: 1.5,
      marginBottom: 20
    }
  }, "Latest reports, presentations, and SEC filings in one place."), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, ["Q2 2026 10-Q", "2025 Annual Report", "Investor Presentation"].map(f => /*#__PURE__*/React.createElement("a", {
    key: f,
    style: {
      cursor: "pointer",
      textDecoration: "none",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      color: "var(--up-off-white)",
      fontSize: 14,
      paddingBottom: 12,
      borderBottom: "1px solid var(--divider-on-dark)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10
    }
  }, /*#__PURE__*/React.createElement(IIcon, {
    name: "file-text",
    size: 16,
    color: "var(--up-green)"
  }), f), /*#__PURE__*/React.createElement(IIcon, {
    name: "download",
    size: 15,
    color: "var(--up-cool-grey)"
  })))), /*#__PURE__*/React.createElement(IButton, {
    variant: "primary",
    fullWidth: true,
    style: {
      marginTop: 22
    },
    onClick: onDemo
  }, "Contact IR")))));
}
function CareersView({
  onDemo
}) {
  const values = [["compass", "Forward-looking", "We move people and outcomes upward."], ["shield-check", "Confident, not loud", "Authoritative without being aggressive."], ["sparkles", "Optimistic", "A sense of possibility runs through everything."]];
  const roles = [["Senior Product Designer", "Design", "Remote — US"], ["Staff Software Engineer", "Engineering", "Plano, TX"], ["Risk Analytics Lead", "Data", "Remote — US"], ["Partnerships Manager", "Growth", "New York, NY"]];
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("section", {
    style: {
      position: "relative",
      background: "var(--up-navy)",
      overflow: "hidden",
      padding: "80px 40px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      inset: "0 -30% 0 60%",
      background: "var(--up-charcoal)",
      transform: "skewX(-30deg)",
      opacity: 0.6
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative",
      maxWidth: 1120,
      margin: "0 auto"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: "0.12em",
      textTransform: "uppercase",
      color: "var(--up-green)",
      marginBottom: 14
    }
  }, "Careers"), /*#__PURE__*/React.createElement("h1", {
    style: {
      color: "var(--up-off-white)",
      fontSize: 52,
      maxWidth: 640
    }
  }, "Build a career that moves people upward."), /*#__PURE__*/React.createElement("p", {
    style: {
      color: "var(--up-cool-grey)",
      marginTop: 18,
      maxWidth: 480,
      fontSize: 17,
      lineHeight: 1.5
    }
  }, "Join a team that makes the complex feel simple \u2014 and takes financial opportunity seriously."))), /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-page)",
      padding: "72px 40px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: 20,
      marginBottom: 64
    }
  }, values.map(([ic, t, b]) => /*#__PURE__*/React.createElement(ICard, {
    key: t,
    padding: 26
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 44,
      height: 44,
      borderRadius: "var(--radius-md)",
      background: "var(--up-navy)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement(IIcon, {
    name: ic,
    size: 22,
    color: "var(--up-green)"
  })), /*#__PURE__*/React.createElement("h3", {
    style: {
      fontSize: 19,
      marginBottom: 8
    }
  }, t), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 15,
      color: "var(--text-muted)",
      lineHeight: 1.5,
      margin: 0
    }
  }, b)))), /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 30,
      marginBottom: 24
    }
  }, "Open roles"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 12
    }
  }, roles.map(([t, d, l]) => /*#__PURE__*/React.createElement(ICard, {
    key: t,
    interactive: true,
    padding: 22,
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 600,
      fontSize: 18,
      color: "var(--text-strong)"
    }
  }, t), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      color: "var(--text-muted)",
      marginTop: 4,
      display: "flex",
      gap: 16
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 6
    }
  }, /*#__PURE__*/React.createElement(IIcon, {
    name: "layers",
    size: 14
  }), d), /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 6
    }
  }, /*#__PURE__*/React.createElement(IIcon, {
    name: "map-pin",
    size: 14
  }), l))), /*#__PURE__*/React.createElement(IButton, {
    variant: "outline",
    size: "sm",
    iconRight: /*#__PURE__*/React.createElement(IIcon, {
      name: "arrow-up-right",
      size: 16
    })
  }, "Apply")))))));
}
Object.assign(window, {
  InvestorsView,
  CareersView
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/InvestorsView.jsx", error: String((e && e.message) || e) }); }

// ui_kits/marketing/SolutionsView.jsx
try { (() => {
// Solutions detail view + sign-in split.
const _NSS = window.UpboundGroupDesignSystem_ca0950;
const {
  Button: SButton,
  Icon: SIcon,
  Card: SCard,
  Tabs: STabs,
  Tag: STag,
  Input: SInput,
  Checkbox: SCheckbox
} = _NSS;
function SolutionsView({
  onDemo
}) {
  const [tab, setTab] = React.useState("Lending");
  const detail = {
    Lending: {
      head: "Fund opportunity in days, not weeks.",
      body: "Configurable underwriting, transparent terms, and real-time decisioning that keeps applicants moving upward.",
      points: ["Automated decisioning", "Transparent, fair terms", "48-hour funding"]
    },
    Payments: {
      head: "Move money with confidence.",
      body: "Real-time settlement, granular controls, and reconciliation your finance team can actually trust.",
      points: ["Real-time settlement", "Ledger-grade controls", "Partner payouts"]
    },
    Marketplace: {
      head: "Financing that meets people where they are.",
      body: "Flexible, opportunity-first financing built into the buying moment for merchants and customers alike.",
      points: ["Embedded checkout", "Flexible terms", "Merchant tools"]
    },
    Analytics: {
      head: "See the whole portfolio clearly.",
      body: "One view of performance, risk, and opportunity — so you act on what actually moves outcomes upward.",
      points: ["Portfolio dashboards", "Risk signals", "Cohort insights"]
    }
  }[tab];
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--up-navy)",
      padding: "64px 40px 40px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: "0.12em",
      textTransform: "uppercase",
      color: "var(--up-green)",
      marginBottom: 14
    }
  }, "Solutions"), /*#__PURE__*/React.createElement("h1", {
    style: {
      color: "var(--up-off-white)",
      fontSize: 46,
      maxWidth: 700
    }
  }, "Everything you need to elevate financial opportunity."))), /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-card)",
      padding: "0 40px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      paddingTop: 8
    }
  }, /*#__PURE__*/React.createElement(STabs, {
    tabs: ["Lending", "Payments", "Marketplace", "Analytics"],
    value: tab,
    onChange: setTab
  })))), /*#__PURE__*/React.createElement("section", {
    style: {
      background: "var(--surface-page)",
      padding: "56px 40px 80px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1120,
      margin: "0 auto",
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 40,
      alignItems: "center"
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 32,
      marginBottom: 16
    }
  }, detail.head), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 17,
      color: "var(--text-muted)",
      lineHeight: 1.55,
      marginBottom: 24
    }
  }, detail.body), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 14,
      marginBottom: 28
    }
  }, detail.points.map(p => /*#__PURE__*/React.createElement("div", {
    key: p,
    style: {
      display: "flex",
      alignItems: "center",
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 24,
      height: 24,
      borderRadius: "50%",
      background: "var(--up-green)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none"
    }
  }, /*#__PURE__*/React.createElement(SIcon, {
    name: "check",
    size: 15,
    color: "var(--up-near-black)"
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 15,
      color: "var(--text-body)"
    }
  }, p)))), /*#__PURE__*/React.createElement(SButton, {
    variant: "primary",
    onClick: onDemo,
    iconRight: /*#__PURE__*/React.createElement(SIcon, {
      name: "arrow-up-right",
      size: 18
    })
  }, "Request a demo")), /*#__PURE__*/React.createElement(SCard, {
    padding: 0,
    style: {
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: "var(--up-navy)",
      padding: "22px 24px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 600,
      fontSize: 16,
      color: "var(--up-off-white)"
    }
  }, tab, " overview"), /*#__PURE__*/React.createElement(STag, {
    selected: true
  }, "Live")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 24,
      display: "flex",
      flexDirection: "column",
      gap: 16
    }
  }, [["Active accounts", "12,480"], ["This month", "+8.2%"], ["Avg. decision", "1.4s"]].map(([k, v]) => /*#__PURE__*/React.createElement("div", {
    key: k,
    style: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      paddingBottom: 14,
      borderBottom: "1px solid var(--border-subtle)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 14,
      color: "var(--text-muted)"
    }
  }, k), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 600,
      fontSize: 20,
      color: "var(--text-strong)"
    }
  }, v))), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 120,
      borderRadius: "var(--radius-md)",
      background: "linear-gradient(180deg, var(--up-off-white), var(--surface-card))",
      border: "1px solid var(--border-subtle)",
      display: "flex",
      alignItems: "flex-end",
      gap: 8,
      padding: 14
    }
  }, [42, 58, 50, 71, 64, 83, 92].map((h, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      flex: 1,
      height: `${h}%`,
      background: i === 6 ? "var(--up-green)" : "var(--up-cool-grey)",
      borderRadius: 4
    }
  }))))))));
}

// Sign-in screen (split navy / form)
function SignInView({
  onNavigate
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      minHeight: 620
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative",
      background: "var(--up-navy)",
      overflow: "hidden",
      padding: "72px 56px",
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: "absolute",
      inset: "40% -40% -30% 30%",
      background: "var(--up-charcoal)",
      transform: "skewX(-30deg)",
      opacity: 0.6
    }
  }), /*#__PURE__*/React.createElement(Wordmark, {
    dark: true
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative"
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      color: "var(--up-off-white)",
      fontSize: 34,
      maxWidth: 380
    }
  }, "Welcome back. Let's keep moving forward."), /*#__PURE__*/React.createElement("p", {
    style: {
      color: "var(--up-cool-grey)",
      marginTop: 16,
      maxWidth: 360,
      fontSize: 15,
      lineHeight: 1.5
    }
  }, "Sign in to your Upbound partner console.")), /*#__PURE__*/React.createElement("span", {
    style: {
      position: "relative",
      fontSize: 13,
      color: "var(--up-cool-grey)"
    }
  }, "\xA9 2026 Upbound Group")), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "var(--surface-card)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: 40
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: "100%",
      maxWidth: 360,
      display: "flex",
      flexDirection: "column",
      gap: 18
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      fontSize: 24
    }
  }, "Sign in"), /*#__PURE__*/React.createElement(SInput, {
    label: "Work email",
    placeholder: "you@company.com",
    iconLeft: /*#__PURE__*/React.createElement(SIcon, {
      name: "mail",
      size: 18
    })
  }), /*#__PURE__*/React.createElement(SInput, {
    label: "Password",
    type: "password",
    placeholder: "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022",
    iconLeft: /*#__PURE__*/React.createElement(SIcon, {
      name: "lock",
      size: 18
    })
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, /*#__PURE__*/React.createElement(SCheckbox, {
    label: "Remember me"
  }), /*#__PURE__*/React.createElement("a", {
    style: {
      cursor: "pointer",
      fontSize: 14
    }
  }, "Forgot?")), /*#__PURE__*/React.createElement(SButton, {
    variant: "primary",
    fullWidth: true,
    onClick: () => onNavigate("home")
  }, "Sign in"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 14,
      color: "var(--text-muted)",
      textAlign: "center",
      margin: 0
    }
  }, "New partner? ", /*#__PURE__*/React.createElement("a", {
    style: {
      cursor: "pointer"
    },
    onClick: () => onNavigate("home")
  }, "Request access")))));
}
Object.assign(window, {
  SolutionsView,
  SignInView
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/marketing/SolutionsView.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Radio = __ds_scope.Radio;

__ds_ns.RadioGroup = __ds_scope.RadioGroup;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Textarea = __ds_scope.Textarea;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.Tooltip = __ds_scope.Tooltip;

})();
