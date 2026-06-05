import { AuthGuard } from "@/components/AuthGuard";
import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";
import { ToastProvider } from "@/components/ui/Toast";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <AuthGuard>
        <div className="flex h-full overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col bg-paper overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-y-auto thin-scroll">{children}</main>
          </div>
        </div>
      </AuthGuard>
    </ToastProvider>
  );
}
