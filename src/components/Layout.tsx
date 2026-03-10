import { ReactNode, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  BellIcon,
  ChatBubbleBottomCenterTextIcon,
  UserCircleIcon,
  PlusIcon,
  ChatBubbleOvalLeftEllipsisIcon
} from "@heroicons/react/24/outline";

interface LayoutProps {
  children: ReactNode;
}

// Верхний уровень каркаса: общий фон, шапка, навигация и контейнер для страниц.
export const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();
  const isAuth = location.pathname.startsWith("/auth");
  const [showNewChatPanel, setShowNewChatPanel] = useState(false);

  // Для /auth показываем упрощённый layout без верхней навигации.
  if (isAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-surface-900 via-surface-900 to-slate-900 flex items-center justify-center px-4">
        {children}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface-900 via-surface-900 to-slate-900 text-slate-50 flex flex-col">
      <header className="relative z-40 border-b border-slate-800/80 bg-surface-900/70 backdrop-blur-xl">
        <div className="relative mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/chats" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-primary-500 to-fuchsia-500 shadow-card" />
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-semibold tracking-wide text-slate-100 uppercase">Vibe Messenger</span>
              <span className="text-[11px] text-slate-400">для онлайн-школы</span>
            </div>
          </Link>
          <div className="flex items-center gap-2 sm:gap-3">
            <nav className="flex items-center gap-4 text-sm font-medium text-slate-300">
              <NavLink
                to="/chats"
                className={({ isActive }) =>
                  `inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs transition ${
                    isActive ? "bg-primary-500/20 text-primary-100" : "hover:bg-slate-800/70 hover:text-slate-100"
                  }`
                }
              >
                <ChatBubbleBottomCenterTextIcon className="h-4 w-4" />
                <span className="hidden text-xs sm:inline">Чаты</span>
              </NavLink>
              <NavLink
                to="/notifications"
                className={({ isActive }) =>
                  `inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs transition ${
                    isActive ? "bg-primary-500/20 text-primary-100" : "hover:bg-slate-800/70 hover:text-slate-100"
                  }`
                }
              >
                <BellIcon className="h-4 w-4" />
                <span className="hidden text-xs sm:inline">Уведомления</span>
              </NavLink>
              <NavLink
                to="/profile"
                className={({ isActive }) =>
                  `inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs transition ${
                    isActive ? "bg-primary-500/20 text-primary-100" : "hover:bg-slate-800/70 hover:text-slate-100"
                  }`
                }
              >
                <UserCircleIcon className="h-4 w-4" />
                <span className="hidden text-xs sm:inline">Профиль</span>
              </NavLink>
            </nav>
            <button
              type="button"
              onClick={() => setShowNewChatPanel((prev) => !prev)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-primary-500/90 text-white shadow-card transition hover:bg-primary-600"
            >
              <PlusIcon className="h-4 w-4" />
            </button>
          </div>

          {showNewChatPanel && (
            <div className="card-surface absolute right-2 top-14 z-50 w-[calc(100vw-2.5rem)] rounded-2xl p-3 text-xs sm:right-4 sm:w-80">
              <div className="mb-1 flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 text-[11px] text-slate-200">
                  <ChatBubbleOvalLeftEllipsisIcon className="h-4 w-4 text-primary-400" />
                  <span className="font-medium">Создать чат</span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowNewChatPanel(false)}
                  className="rounded-full px-2 py-0.5 text-[10px] text-slate-400 hover:bg-slate-800/70 hover:text-slate-100"
                >
                  закрыть
                </button>
              </div>
              <p className="mb-2 text-[11px] text-slate-400">
                В полной версии здесь будет форма создания личных и групповых чатов для потоков и курсов.
              </p>
              <div className="grid gap-2 text-[11px]">
                <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 px-3 py-2">
                  <div className="mb-0.5 text-slate-200">Личный чат</div>
                  <div className="text-slate-500">Например, общение с куратором или студентом один на один.</div>
                </div>
                <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 px-3 py-2">
                  <div className="mb-0.5 text-slate-200">Групповой чат</div>
                  <div className="text-slate-500">
                    Небольшие команды внутри потока, проектные группы и чаты модуля.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 px-4 py-4 sm:py-6">{children}</main>
    </div>
  );
};

