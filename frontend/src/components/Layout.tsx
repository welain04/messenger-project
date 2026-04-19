import { ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  BellIcon,
  ChatBubbleBottomCenterTextIcon,
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
} from "@heroicons/react/24/outline";
import logoAsterisk from "../assets/logo-asterisk.png";
import { useAuth } from "../auth/AuthContext";

interface LayoutProps {
  children: ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const isAuth = location.pathname.startsWith("/auth");

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
            {user && (
              <div className="hidden items-center gap-2 text-[11px] text-slate-500 sm:flex">
                <span>
                  <span className="text-slate-400">Вы:</span> <span className="font-medium text-slate-700">{user.nickname}</span>
                </span>
                <button
                  type="button"
                  onClick={() => { logout(); navigate("/auth", { replace: true }); }}
                  title="Выйти"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
                >
                  <ArrowRightOnRectangleIcon className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 px-4 py-6 sm:py-10">{children}</main>
    </div>
  );
};
