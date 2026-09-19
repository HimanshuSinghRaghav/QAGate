import Link from "next/link";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
} from "react";
import { cn } from "@/lib/cn";

type ButtonVariant = "primary" | "secondary" | "ghost" | "link" | "danger";

const buttonClass: Record<ButtonVariant, string> = {
  primary:
    "inline-flex h-9 items-center justify-center rounded-full bg-primary px-4 type-button-md text-on-primary active:bg-charcoal disabled:bg-hairline disabled:text-muted",
  secondary:
    "inline-flex h-9 items-center justify-center rounded-full border border-hairline-strong bg-canvas px-4 type-button-md text-ink active:bg-surface",
  ghost:
    "inline-flex h-9 items-center justify-center rounded-md px-3 type-button-md text-ink active:bg-surface",
  link: "inline-flex items-center type-body-sm-medium text-brand-blue p-0",
  danger:
    "inline-flex h-9 items-center justify-center rounded-full bg-coral-dark px-4 type-button-md text-on-primary",
};

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return <button className={cn(buttonClass[variant], className)} {...props} />;
}

export function ButtonLink({
  variant = "primary",
  className,
  href,
  children,
}: {
  variant?: ButtonVariant;
  className?: string;
  href: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className={cn(buttonClass[variant], className)}>
      {children}
    </Link>
  );
}

export function Badge({
  tone = "yellow",
  children,
  className,
}: {
  tone?: "yellow" | "purple" | "coral" | "success" | "promo" | "neutral";
  children: ReactNode;
  className?: string;
}) {
  const tones = {
    yellow: "bg-surface-yellow text-yellow-dark",
    purple: "bg-surface-pricing-featured text-brand-blue",
    coral: "bg-coral-light text-coral-dark",
    success: "bg-success-accent text-on-primary",
    promo: "bg-brand-yellow text-primary",
    neutral: "bg-surface text-slate",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 type-caption-bold",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Panel({
  className,
  children,
}: {
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-hairline bg-canvas",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function TextInput({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-md border border-hairline-strong bg-canvas px-sm type-body-sm text-ink placeholder:text-muted focus:border-2 focus:border-brand-blue focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}

export function TextArea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-md border border-hairline-strong bg-canvas px-sm py-xs type-body-sm text-ink placeholder:text-muted focus:border-2 focus:border-brand-blue focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}

export function SearchField({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-md border border-hairline bg-surface px-sm type-body-sm text-ink placeholder:text-muted focus:border-brand-blue focus:outline-none",
        className,
      )}
      {...props}
    />
  );
}

export function PillTab({
  active,
  children,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      className={cn(
        "inline-flex h-8 items-center rounded-full border px-sm type-body-sm-medium",
        active
          ? "border-primary bg-primary text-on-primary"
          : "border-hairline bg-canvas text-steel",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function PillTabLink({
  href,
  active,
  children,
}: {
  href: string;
  active?: boolean;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex h-8 items-center rounded-full border px-sm type-body-sm-medium",
        active
          ? "border-primary bg-primary text-on-primary"
          : "border-hairline bg-canvas text-steel",
      )}
    >
      {children}
    </Link>
  );
}

export function EmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <Panel className="px-xl py-xxl text-center">
      <p className="type-heading-5 text-ink">{title}</p>
      <p className="mt-xs type-body-sm text-slate">{body}</p>
    </Panel>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-md flex flex-col gap-sm border-b border-hairline-soft pb-md lg:flex-row lg:items-end lg:justify-between">
      <div>
        {eyebrow ? (
          <p className="type-micro-uppercase text-stone">{eyebrow}</p>
        ) : null}
        <h1 className="type-heading-4 text-ink">{title}</h1>
        {description ? (
          <p className="mt-xxs max-w-2xl type-caption text-slate">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-xs">{actions}</div> : null}
    </div>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <dt className="type-caption text-stone">{label}</dt>
      <dd className="type-body-sm-medium text-ink">{children}</dd>
    </div>
  );
}
