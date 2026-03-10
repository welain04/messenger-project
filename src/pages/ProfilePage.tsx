import { currentUser } from "../mockData";

// Страница профиля: базовая информация об ученике и курсах (пока без реальных курсов).
export const ProfilePage = () => {
  return (
    <section className="card-surface flex w-full flex-col gap-5 rounded-2xl p-4 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-500 text-lg font-semibold text-white shadow-card">
            {currentUser.name[0]}
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-slate-900">Профиль: {currentUser.name}</h2>
            <p className="text-xs text-slate-600">
              Роль: {currentUser.role === "student" ? "Ученик" : "Куратор"} · доступ к чатам онлайн‑школы
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Контактные данные
          </h3>
          <div className="space-y-2 text-xs text-slate-700">
            <div>
              <div className="text-[11px] text-slate-500">Email</div>
              <div>you@example.com</div>
            </div>
            <div>
              <div className="text-[11px] text-slate-500">Telegram / WhatsApp</div>
              <div>@your_username</div>
            </div>
          </div>
          <p className="mt-3 text-[11px] text-slate-500">
            В реальном продукте здесь будет форма редактирования данных с сохранением на сервер.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Безопасность и приватность
          </h3>
          <ul className="space-y-2 text-xs text-slate-700">
            <li className="flex items-center justify-between gap-2">
              <span>Разрешить личные сообщения от одногруппников</span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-emerald-600">
                Будет доступно позже
              </span>
            </li>
            <li className="flex items-center justify-between gap-2">
              <span>Двухфакторная аутентификация</span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">
                В прототипе выключена
              </span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
};

