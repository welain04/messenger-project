import { ReactNode, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  BellIcon,
  ChatBubbleBottomCenterTextIcon,
  UserCircleIcon,
  PlusIcon,
  ChatBubbleOvalLeftEllipsisIcon
} from "@heroicons/react/24/outline";
import logoAsterisk from "../assets/logo-asterisk.png";

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
      <div className="min-h-screen bg-surface-900 flex items-center justify-center px-4">
        {children}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-900 text-slate-900 flex flex-col">
      <header className="relative z-40 border-b border-slate-200 bg-white/90 backdrop-blur-md">
        <div className="relative mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link to="/chats" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#b3daf6] shadow-card overflow-hidden">
              <img src={logoAsterisk} alt="Vibe Messenger логотип" className="h-5 w-5 object-contain" />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-xs font-semibold tracking-[0.18em] text-slate-700 uppercase">
                Vibe · Messenger
              </span>
              <span className="text-xs text-slate-500">пространство общения по курсу</span>
            </div>
          </Link>
          <div className="flex items-center gap-2 sm:gap-3">
            <nav className="flex items-center gap-2 rounded-full bg-slate-100 px-1.5 py-1 text-xs font-medium text-slate-600 shadow-sm">
              <NavLink
                to="/chats"
                className={({ isActive }) =>
                  `inline-flex items-center gap-1 rounded-full px-2.5 py-1 transition ${
                    isActive
                      ? "bg-primary-500 text-white shadow-card"
                      : "hover:bg-white hover:text-slate-900"
                  }`
                }
              >
                <ChatBubbleBottomCenterTextIcon className="h-4 w-4" />
                <span className="hidden text-xs sm:inline">Чаты</span>
              </NavLink>
              <NavLink
                to="/notifications"
                className={({ isActive }) =>
                  `inline-flex items-center gap-1 rounded-full px-2.5 py-1 transition ${
                    isActive ? "bg-primary-50 text-primary-700" : "hover:bg-white hover:text-slate-900"
                  }`
                }
              >
                <BellIcon className="h-4 w-4" />
                <span className="hidden text-xs sm:inline">Уведомления</span>
              </NavLink>
              <NavLink
                to="/profile"
                className={({ isActive }) =>
                  `inline-flex items-center gap-1 rounded-full px-2.5 py-1 transition ${
                    isActive ? "bg-primary-50 text-primary-700" : "hover:bg-white hover:text-slate-900"
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
              className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-primary-500 text-white shadow-card transition hover:bg-primary-600"
            >
              <PlusIcon className="h-4 w-4" />
            </button>
          </div>

          {showNewChatPanel && (
            <div className="card-surface absolute right-2 top-14 z-50 w-[calc(100vw-2.5rem)] rounded-2xl p-3 text-xs sm:right-4 sm:w-80">
              <div className="mb-1 flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 text-[11px] text-slate-700">
                  <ChatBubbleOvalLeftEllipsisIcon className="h-4 w-4 text-primary-500" />
                  <span className="font-medium">Создать чат</span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowNewChatPanel(false)}
                  className="rounded-full px-2 py-0.5 text-[10px] text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                >
                  закрыть
                </button>
              </div>
              <p className="mb-2 text-[11px] text-slate-500">
                В полной версии здесь будет форма создания личных и групповых чатов для потоков и курсов.
              </p>
              <div className="grid gap-2 text-[11px]">
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                  <div className="mb-0.5 text-slate-800">Личный чат</div>
                  <div className="text-slate-500">Например, общение с куратором или студентом один на один.</div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                  <div className="mb-0.5 text-slate-800">Групповой чат</div>
                  <div className="text-slate-500">
                    Небольшие команды внутри потока, проектные группы и чаты модуля.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 px-4 py-6 sm:py-10">{children}</main>
    </div>
  );
};

