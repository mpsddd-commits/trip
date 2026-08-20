/**
 * W16 SharedUi — 기본 UI 요소.
 *
 * 근거:
 *   NFR-6 / WBR-38  키보드 조작 가능, `aria-label`, **색상만으로 정보 전달 금지**
 *   WBR-39          최소 폭 360px
 *   SEC-04          인라인 `<script>` 를 만들지 않는다 (스타일은 CSS 클래스로)
 *
 * 스타일은 클래스 이름만 부여한다. 실제 CSS 는 `styles.css` 에 있다.
 */
import type { ButtonHTMLAttributes, ReactNode } from "react";

// ---------------------------------------------------------------------------
type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: ReactNode;
}

export function Button({ variant = "secondary", children, ...rest }: ButtonProps) {
  return (
    <button type="button" className={`btn btn--${variant}`} {...rest}>
      {children}
    </button>
  );
}

// ---------------------------------------------------------------------------
export type BadgeTone = "info" | "warn" | "danger" | "neutral";

/**
 * WBR-38 — 배지는 **항상 텍스트를 포함**한다. 색상만으로 의미를 전달하지 않는다.
 * 아이콘만 쓰는 배지는 만들지 않는다.
 */
export function Badge({ tone = "neutral", children, title }: { tone?: BadgeTone; children: ReactNode; title?: string }) {
  return (
    <span className={`badge badge--${tone}`} title={title}>
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
/**
 * WBR-30 — 데모 모드 배너는 **닫을 수 없다**.
 * 데모 데이터를 실제 정보로 오해하는 것을 막기 위한 의도적 선택이다.
 */
export function Banner({
  tone = "info",
  dismissible = false,
  onDismiss,
  children,
}: {
  tone?: BadgeTone;
  dismissible?: boolean;
  onDismiss?: () => void;
  children: ReactNode;
}) {
  return (
    <div className={`banner banner--${tone}`} role="status" aria-live="polite">
      <div className="banner__content">{children}</div>
      {dismissible ? (
        <button type="button" className="banner__close" aria-label="알림 닫기" onClick={onDismiss}>
          ✕
        </button>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
export function Skeleton({ lines = 3, label = "불러오는 중" }: { lines?: number; label?: string }) {
  return (
    <div className="skeleton" role="status" aria-label={label}>
      {Array.from({ length: lines }, (_, index) => (
        <div key={index} className="skeleton__line" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
/** 데스크톱은 사이드 패널, 모바일은 바텀 시트로 렌더링된다 (CSS 미디어 쿼리). */
export function Sheet({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="sheet-overlay" onClick={onClose} role="presentation">
      <section
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="sheet__header">
          <h2 className="sheet__title">{title}</h2>
          <button type="button" className="sheet__close" aria-label="닫기" onClick={onClose}>
            ✕
          </button>
        </header>
        <div className="sheet__body">{children}</div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
export interface ToastItem {
  id: string;
  tone: BadgeTone;
  message: string;
  /** WBR-33 — 접어둔 상세에만 노출한다 */
  correlationId?: string | null;
}

export function ToastHost({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: string) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div className="toast-host" aria-live="assertive">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast--${toast.tone}`} role="alert">
          <span className="toast__message">{toast.message}</span>
          {toast.correlationId ? (
            <details className="toast__details">
              <summary>자세히</summary>
              <code>{toast.correlationId}</code>
            </details>
          ) : null}
          <button type="button" aria-label="알림 닫기" onClick={() => onDismiss(toast.id)}>
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <p className="empty-state__title">{title}</p>
      {description ? <p className="empty-state__description">{description}</p> : null}
      {action}
    </div>
  );
}
