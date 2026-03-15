import { mockNotifications } from "../mockData";

// Страница уведомлений: упрощённый список событий без «шума» от новых сообщений.
export const NotificationsPage = () => {
  // На этой странице не показываем уведомления о новых сообщениях.
  const items = mockNotifications.filter((n) => n.type !== "message");
  const unreadCount = items.filter((n) => !n.read).length;

  return (
    <section className="card-surface flex w-full flex-col rounded-2xl p-4 sm:p-6">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-900 sm:text-xl">Уведомления</h2>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
          Непрочитано: {unreadCount}
        </span>
      </div>

      <div className="mt-4 space-y-2 text-xs">
        {items.map((notification) => (
          <div
            key={notification.id}
            className={`flex items-start justify-between gap-3 rounded-2xl border px-3 py-2.5 ${
              notification.read
                ? "border-slate-200 bg-slate-50 text-slate-700"
                : "border-primary-100 bg-primary-50 text-slate-800"
            }`}
          >
            <div className="flex-1">
              <div className="mb-1 flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                    notification.type === "mention"
                      ? "bg-primary-100 text-primary-700"
                      : "bg-slate-100 text-slate-700"
                  }`}
                >
                  {notification.type === "mention" ? "Упоминание" : "Система"}
                </span>
                {!notification.read && (
                  <span className="text-[10px] text-primary-600">новое</span>
                )}
              </div>
              <p>{notification.text}</p>
            </div>
            <div className="shrink-0 text-[10px] text-slate-400">{notification.createdAt}</div>
          </div>
        ))}
      </div>
    </section>
  );
};

