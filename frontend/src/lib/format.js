import { format, formatDistanceToNowStrict, isToday, isTomorrow, isYesterday } from "date-fns";

export function toDate(v) {
  if (!v) return null;
  const d = new Date(v);
  return isNaN(d.getTime()) ? null : d;
}

export function fmtWhen(v, withTime = true) {
  const d = toDate(v);
  if (!d) return "";
  const t = withTime ? `, ${format(d, "HH:mm")}` : "";
  if (isToday(d)) return `Today${t}`;
  if (isTomorrow(d)) return `Tomorrow${t}`;
  if (isYesterday(d)) return `Yesterday${t}`;
  return format(d, withTime ? "EEE d MMM, HH:mm" : "EEE d MMM");
}

export function fmtTime(v) {
  const d = toDate(v);
  return d ? format(d, "HH:mm") : "";
}

export function fmtAgo(v) {
  const d = toDate(v);
  return d ? `${formatDistanceToNowStrict(d)} ago` : "";
}

export function toLocalInput(v) {
  const d = toDate(v);
  if (!d) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fromLocalInput(v) {
  if (!v) return null;
  const d = new Date(v);
  return isNaN(d.getTime()) ? null : d.toISOString();
}

const SYMBOLS = { INR: "₹", USD: "$", EUR: "€", GBP: "£", AED: "AED ", SGD: "S$", AUD: "A$", NGN: "₦", KES: "KSh ", ZAR: "R", JPY: "¥", BDT: "৳", PKR: "Rs ", LKR: "Rs ", NPR: "Rs ", IDR: "Rp ", MYR: "RM ", PHP: "₱", SAR: "SAR ", BRL: "R$", MXN: "MX$", CAD: "C$" };

export function money(amount, currency) {
  if (amount === null || amount === undefined || amount === "") return "";
  const sym = SYMBOLS[(currency || "").toUpperCase()] ?? (currency ? `${currency} ` : "");
  const n = Number(amount);
  return `${sym}${isNaN(n) ? amount : n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export const KIND_LABEL = { task: "Task", promise: "Promise", reminder: "Reminder", decision: "Decision", note: "Personal note" };

export function absoluteUrl(u) {
  if (!u) return u;
  if (u.startsWith("http")) return u;
  return `${window.location.origin}${u.startsWith("/") ? "" : "/"}${u}`;
}

export function initials(name) {
  return (name || "?")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0].toUpperCase())
    .join("");
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
