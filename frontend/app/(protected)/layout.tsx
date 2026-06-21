import { NavBar } from "@/components/NavBar";

/**
 * Layout for all protected pages (/chat, /pending).
 * The middleware ensures only authenticated users reach here.
 * NavBar handles user fetching and logout.
 */
export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-zinc-950">
      <NavBar />
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
