"use client";

import { Avatar } from "@/components/ui/Avatar";
import { Icon } from "@/components/ui/icons";
import { Input } from "@/components/ui/Input";
import { useCurrentUser } from "@/lib/queries";
import { clearTokens } from "@/lib/api";
import { useRouter } from "next/navigation";

export function TopBar() {
  const { data: user } = useCurrentUser();
  const router = useRouter();

  function signOut() {
    clearTokens();
    router.push("/login");
  }

  const displayName =
    user?.full_name
      ? user.full_name.split(" ").slice(0, 2).join(" ")
      : user?.email ?? "";

  return (
    <header className="h-[52px] shrink-0 bg-surface hair-b flex items-center px-4 gap-3">
      <div className="flex-1 max-w-[480px]">
        <Input
          icon={<Icon.search size={14} />}
          placeholder="Doküman, sipariş ya da müşteri ara…"
          suffix={<kbd>⌘K</kbd>}
        />
      </div>

      <div className="flex-1" />

      <button className="h-8 px-2.5 rounded-md hover:bg-ink-100 text-ink-700 text-[12.5px] inline-flex items-center gap-1.5 transition-colors">
        <Icon.bolt size={14} />
        <span>Hızlı işlem</span>
      </button>

      <button className="h-8 w-8 rounded-md hover:bg-ink-100 text-ink-700 inline-flex items-center justify-center relative transition-colors">
        <Icon.bell size={16} />
        <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-warn" />
      </button>

      <div className="h-6 w-px bg-ink-200 mx-1" />

      <button className="inline-flex items-center gap-2 h-8 pl-1 pr-2 rounded-md hover:bg-ink-100 transition-colors">
        <Avatar name={displayName || "U"} size={26} tone="accent" />
        {displayName && (
          <span className="text-[12.5px] text-ink-800 font-medium max-w-[100px] truncate">
            {displayName}
          </span>
        )}
        <Icon.chevD size={14} className="text-ink-500" />
      </button>

      <button
        onClick={signOut}
        title="Çıkış"
        className="h-8 w-8 rounded-md hover:bg-ink-100 text-ink-600 inline-flex items-center justify-center transition-colors"
      >
        <Icon.logout size={15} />
      </button>
    </header>
  );
}
