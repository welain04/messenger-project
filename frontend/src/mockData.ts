// Centralised mock data for V1. In реальном приложении эти структуры
// будут приходить с сервера, но сейчас нам важна только форма данных.

export type UserRole = "student" | "mentor";

export interface User {
  id: string;
  name: string;
  role: UserRole;
}

export interface ChatSummary {
  id: string;
  title: string;
  type: "direct" | "group" | "course";
  lastMessage: string;
  lastTime: string;
  unread: number;
}

export interface Message {
  id: string;
  chatId: string;
  authorId: string;
  text: string;
  createdAt: string;
  isOwn: boolean;
}

export interface NotificationItem {
  id: string;
  type: "message" | "system" | "mention";
  text: string;
  createdAt: string;
  read: boolean;
}

export const currentUser: User = {
  id: "u1",
  name: "Саша",
  role: "student"
};

export const mockChats: ChatSummary[] = [
  {
    id: "c1",
    title: "Курс · Vibe Coding 1 поток",
    type: "course",
    lastMessage: "Куратор: завтра созвон в 19:00 👋",
    lastTime: "18:42",
    unread: 3
  },
  {
    id: "c2",
    title: "Личный · Куратор Анна",
    type: "direct",
    lastMessage: "Как продвигается ДЗ по третьему модулю?",
    lastTime: "16:10",
    unread: 0
  },
  {
    id: "c3",
    title: "Группа · Команда Project A",
    type: "group",
    lastMessage: "Максим: я запушил обновлённый макет",
    lastTime: "15:27",
    unread: 5
  }
];

export const mockMessages: Message[] = [
  {
    id: "m1",
    chatId: "c1",
    authorId: "mentor1",
    text: "Привет! Добро пожаловать в чат курса. Здесь мы общаемся по всем вопросам по программе ✨",
    createdAt: "10:01",
    isOwn: false
  },
  {
    id: "m2",
    chatId: "c1",
    authorId: "u1",
    text: "Спасибо! Где найти записи прошлых созвонов?",
    createdAt: "10:05",
    isOwn: true
  },
  {
    id: "m3",
    chatId: "c1",
    authorId: "mentor1",
    text: "Все записи лежат в Notion, вот ссылка в закрепе чата 🔗",
    createdAt: "10:06",
    isOwn: false
  },
  {
    id: "m4",
    chatId: "c2",
    authorId: "mentor1",
    text: "Саша, привет! Я посмотрела твоё ДЗ, есть пара идей как улучшить архитектуру.",
    createdAt: "16:05",
    isOwn: false
  }
];

export const mockNotifications: NotificationItem[] = [
  {
    id: "n1",
    type: "message",
    text: "Новое сообщение от куратора в чате «Vibe Coding 1 поток»",
    createdAt: "18:42",
    read: false
  },
  {
    id: "n2",
    type: "mention",
    text: "Вас упомянули в чате «Команда Project A»",
    createdAt: "17:01",
    read: false
  },
  {
    id: "n3",
    type: "system",
    text: "Вас добавили в курс «Vibe Coding»",
    createdAt: "09:15",
    read: true
  }
];

