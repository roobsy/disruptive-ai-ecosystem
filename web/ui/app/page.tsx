import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Dashboard } from "@/components/dashboard/dashboard";
import { ChatPanel } from "@/components/chat/chat-panel";

export default function HomePage() {
  return (
    <div className="h-screen flex bg-bg overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto">
          <Dashboard />
        </main>
      </div>
      <div className="w-[400px] shrink-0 hidden lg:flex">
        <ChatPanel />
      </div>
    </div>
  );
}
