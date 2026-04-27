"use client";

import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import useSWR from "swr";

interface User {
  id: number;
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
}

const roleBadge: Record<string, { bg: string; text: string; icon: string }> = {
  admin: { bg: "bg-destructive/10", text: "text-destructive", icon: "solar:shield-user-bold" },
  signer: { bg: "bg-warning/10", text: "text-warning", icon: "solar:pen-new-square-bold" },
  viewer: { bg: "bg-primary/10", text: "text-primary", icon: "solar:eye-bold" },
};

export default function UsersPage() {
  const { data: users, error, isLoading } = useSWR<User[]>(
    "/api/users",
    async () => {
      const data = await api.get("/api/users");
      return Array.isArray(data) ? data : data.users || data.items || [];
    }
  );

  return (
    <>
      <Header title="Пользователи" />
      <div className={pageLayout.container}>
        {/* Stats */}
        {users && users.length > 0 && (
          <div className={pageLayout.grid.cols3}>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-primary/10 p-2.5">
                  <Icon icon="solar:users-group-rounded-bold" className="text-xl text-primary dark:text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{users.length}</p>
                  <p className="text-xs text-muted-foreground">Всего пользователей</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-success/10 p-2.5">
                  <Icon icon="solar:check-circle-bold" className="text-xl text-success" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{users.filter(u => u.is_active).length}</p>
                  <p className="text-xs text-muted-foreground">Активных</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-destructive/10 p-2.5">
                  <Icon icon="solar:shield-user-bold" className="text-xl text-destructive" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{users.filter(u => u.role === 'admin').length}</p>
                  <p className="text-xs text-muted-foreground">Администраторов</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {isLoading && (
          <Card>
            <div className="p-8 text-center">
              <Icon icon="solar:refresh-linear" className="mx-auto text-3xl text-muted-foreground animate-spin mb-3" />
              <p className="text-sm text-muted-foreground">Загрузка пользователей...</p>
            </div>
          </Card>
        )}

        {error && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4">
            <p className="text-sm text-destructive">Не удалось загрузить пользователей</p>
          </div>
        )}

        {/* Desktop Table */}
        {users && users.length > 0 && (
          <>
            {/* Mobile cards */}
            <div className="space-y-3 md:hidden">
              {users.map((u) => {
                const badge = roleBadge[u.role] || roleBadge.viewer;
                return (
                  <Card key={u.id}>
                    <div className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                            <span className="text-sm font-bold text-primary dark:text-primary">
                              {(u.full_name || u.email)[0].toUpperCase()}
                            </span>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-foreground">{u.full_name || "—"}</p>
                            <p className="text-xs text-muted-foreground">{u.email}</p>
                          </div>
                        </div>
                        <span className={`inline-flex items-center gap-1 text-xs ${u.is_active ? "text-success" : "text-destructive"}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${u.is_active ? "bg-success" : "bg-destructive"}`} />
                          {u.is_active ? "Активен" : "Неактивен"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-2">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${badge.bg} ${badge.text}`}>
                          <Icon icon={badge.icon} className="text-xs" />
                          {u.role}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {u.created_at ? new Date(u.created_at).toLocaleDateString('ru-RU') : "—"}
                        </span>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>

            {/* Desktop table */}
            <div className="hidden md:block">
              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border bg-muted/50 dark:border-border dark:bg-card/50">
                      <tr>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Пользователь</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Роль</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Статус</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Последний вход</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Создан</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {users.map((u) => {
                        const badge = roleBadge[u.role] || roleBadge.viewer;
                        return (
                          <tr key={u.id} className="hover:bg-muted dark:hover:bg-muted/50 transition-colors">
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                                  <span className="text-sm font-bold text-primary dark:text-primary">
                                    {(u.full_name || u.email)[0].toUpperCase()}
                                  </span>
                                </div>
                                <div>
                                  <p className="text-sm font-medium text-foreground">{u.full_name || "—"}</p>
                                  <p className="text-xs text-muted-foreground">{u.email}</p>
                                </div>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${badge.bg} ${badge.text}`}>
                                <Icon icon={badge.icon} className="text-xs" />
                                {u.role}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center gap-1.5 text-xs ${u.is_active ? "text-success" : "text-destructive"}`}>
                                <span className={`h-2 w-2 rounded-full ${u.is_active ? "bg-success" : "bg-destructive"}`} />
                                {u.is_active ? "Активен" : "Неактивен"}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-xs text-muted-foreground">
                              {u.last_login_at ? new Date(u.last_login_at).toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : "—"}
                            </td>
                            <td className="px-4 py-3 text-xs text-muted-foreground">
                              {u.created_at ? new Date(u.created_at).toLocaleDateString('ru-RU') : "—"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          </>
        )}

        {users && users.length === 0 && (
          <Card>
            <div className="p-8 text-center">
              <Icon icon="solar:users-group-rounded-linear" className="mx-auto text-5xl text-faint dark:text-muted-foreground mb-4" />
              <h2 className="text-lg font-semibold text-foreground mb-2">Нет пользователей</h2>
              <p className="text-sm text-muted-foreground">Пользователи не найдены</p>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
