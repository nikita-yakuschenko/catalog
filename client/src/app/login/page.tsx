"use client";

import { IconLogin } from "@tabler/icons-react";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function LoginPage() {
  const { loading, status } = useAuth();

  if (loading) {
    return <p className="text-sm text-muted-foreground">Проверка сессии…</p>;
  }

  if (status && !status.auth_enabled) {
    return (
      <div className="space-y-4">
        <PageHeader
          eyebrow="Auth"
          title="Авторизация отключена"
          description="BITRIX_OAUTH_CLIENT_ID не задан — UI открыт без входа (режим разработки)."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-8">
      <PageHeader
        eyebrow="Bitrix24"
        title="Вход в Catalog Builder"
        description="Войдите учётной записью сотрудника портала AVGST. Доступ только для пользователей вашего Bitrix24."
      />
      <a href={api.loginUrl()} className={cn(buttonVariants({ size: "lg" }), "inline-flex")}>
        <IconLogin className="size-4" stroke={1.75} />
        Войти через Bitrix24
      </a>
    </div>
  );
}
