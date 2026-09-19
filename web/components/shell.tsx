"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type ReactNode } from "react";
import { SearchField } from "@/components/ui";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "Home", match: (p: string) => p === "/" },
  { href: "/queue", label: "Inbox", match: (p: string) => p.startsWith("/queue") },
  { href: "/leads", label: "Leads", match: (p: string) => p.startsWith("/leads") },
  { href: "/checks", label: "Playbooks", match: (p: string) => p.startsWith("/checks") },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-surface">
      <aside
        className={cn(
          "z-40 flex w-56 shrink-0 flex-col border-r border-hairline bg-canvas",
          "fixed inset-y-0 left-0 lg:static",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
        <Link href="/" className="flex items-center gap-xs border-b border-hairline-soft px-md py-sm">
          <span className="flex size-7 items-center justify-center rounded-sm bg-brand-yellow type-caption-bold text-primary">
            QA
          </span>
          <span className="type-body-md-medium text-ink">Gate</span>
        </Link>
        <nav className="flex-1 px-xs py-sm">
          {NAV.map((item) => {
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "mb-xxs flex h-9 items-center rounded-md px-sm type-body-sm-medium",
                  active ? "bg-primary text-on-primary" : "text-slate",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-hairline-soft px-md py-sm">
          <p className="type-caption-bold text-ink">Priya Nair</p>
          <p className="type-caption text-stone">Team lead · FibreLink</p>
        </div>
      </aside>

      {open ? (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-30 bg-ink/40 lg:hidden"
          onClick={() => setOpen(false)}
        />
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-12 items-center gap-sm border-b border-hairline bg-canvas px-md">
          <button
            type="button"
            aria-label="Menu"
            className="flex size-9 items-center justify-center rounded-full border border-hairline lg:hidden"
            onClick={() => setOpen(true)}
          >
            <span className="flex flex-col gap-1">
              <span className="block h-0.5 w-3.5 bg-ink" />
              <span className="block h-0.5 w-3.5 bg-ink" />
              <span className="block h-0.5 w-3.5 bg-ink" />
            </span>
          </button>
          <div className="w-[320px] shrink-0">
            <Suspense fallback={<div className="h-9 rounded-md bg-surface" />}>
              <GlobalSearch />
            </Suspense>
          </div>
          <Link href="/queue?decision=HELD" className="type-body-sm-medium text-brand-blue">
            Open inbox
          </Link>
        </header>
        <main className="min-w-0 flex-1 p-md lg:p-lg">{children}</main>
      </div>
    </div>
  );
}

function GlobalSearch() {
  const params = useSearchParams();
  return (
    <form action="/leads" className="w-full">
      <SearchField
        name="q"
        placeholder="Search customer, lead or agent…"
        defaultValue={params.get("q") ?? ""}
      />
    </form>
  );
}

export function ClickRow({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  const router = useRouter();
  return (
    <tr
      tabIndex={0}
      onClick={() => router.push(href)}
      onKeyDown={(event) => {
        if (event.key === "Enter") router.push(href);
      }}
      className="cursor-pointer border-t border-hairline-soft active:bg-surface-yellow"
    >
      {children}
    </tr>
  );
}
