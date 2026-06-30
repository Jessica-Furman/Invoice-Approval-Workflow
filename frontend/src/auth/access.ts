/**
 * Access rules for who may sign up / sign in.
 *
 * The product rule: only Upbound Group or Rent-A-Center (RAC) employees get in, and they must
 * supply an employee ID. For now this is enforced client-side only as a visual/UX guard — the
 * REAL enforcement will live in the backend signup endpoint + OAuth (an unverified client can
 * trivially bypass this). Keep the constants here so backend validation can mirror them later.
 *
 * Edit this one list and both pages update. Backend signup validation should mirror these.
 */
export const ALLOWED_EMAIL_DOMAINS = ["upbound.com", "rentacenter.com", "acima.com"] as const;

/** Employee IDs are exactly 6 digits. */
const EMPLOYEE_ID_RE = /^\d{6}$/;

export function emailDomain(email: string): string {
  const at = email.lastIndexOf("@");
  return at === -1 ? "" : email.slice(at + 1).toLowerCase().trim();
}

export function isAllowedEmail(email: string): boolean {
  const domain = emailDomain(email);
  return (ALLOWED_EMAIL_DOMAINS as readonly string[]).includes(domain);
}

export function isValidEmployeeId(employeeId: string): boolean {
  return EMPLOYEE_ID_RE.test(employeeId.trim());
}

/** Human-readable "who can join" hint shown under the signup form. */
export const ACCESS_HINT = `Use your ${ALLOWED_EMAIL_DOMAINS.join(" or ")} email and employee ID.`;
