import { useCallback, useEffect, useState } from "react";
import { formatApiError, notificationsApi } from "../api";
import type { Notification } from "../api";
import { ErrorBox, LoadingHint } from "../components/States";

const formatDateTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

export const NotificationsPage = () => {
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markingId, setMarkingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await notificationsApi.list();
      setItems(data);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleMarkRead = async (id: string) => {
    setMarkingId(id);
    try {
      const updated = await notificationsApi.markRead(id);
      setItems((prev) => prev.map((n) => (n.id === id ? updated : n)));
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setMarkingId(null);
    }
  };

  const unreadCount = items.filter((n) => !n.is_read).length;

  return (
    <section className="card-surface flex w-full flex-col rounded-2xl p-4 sm:p-6">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-900 sm:text-xl">Уведомления</h2>
        <div className="flex items-center gap-3">
          {loading && <LoadingHint text="Обновление" />}
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
            Непрочитано: {unreadCount}
          </span>
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="rounded-full border border-slate-200 px-2.5 py-0.5 text-[11px] hover:bg-slate-100"
          >
            Обновить
          </button>
        </div>
      </div>

      {error && <div className="mb-3"><ErrorBox message={error} onRetry={load} /></div>}

      {!loading && !error && items.length === 0 && (
        <p className="py-8 text-center text-xs text-slate-500">Уведомлений пока нет.</p>
      )}

      <div className="mt-2 space-y-2 text-xs">
        {items.map((notification) => (
          <div
            key={notification.id}
            className={`flex items-start justify-between gap-3 rounded-2xl border px-3 py-2.5 ${
              notification.is_read
                ? "border-slate-200 bg-slate-50 text-slate-700"
                : "border-primary-100 bg-primary-50 text-slate-800"
            }`}
          >
            <div className="flex-1">
              <div className="mb-1 flex items-center gap-2">
                {!notification.is_read && (
                  <span className="rounded-full bg-primary-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary-700">
                    новое
                  </span>
                )}
              </div>
              <p>{notification.message}</p>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <div className="text-[10px] text-slate-400">{formatDateTime(notification.created_at)}</div>
              {!notification.is_read && (
                <button
                  type="button"
                  onClick={() => handleMarkRead(notification.id)}
                  disabled={markingId === notification.id}
                  className="rounded-full border border-primary-200 bg-white px-2 py-0.5 text-[10px] font-medium text-primary-700 hover:bg-primary-50 disabled:opacity-60"
                >
                  {markingId === notification.id ? "…" : "Прочитано"}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
