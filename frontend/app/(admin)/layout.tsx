import { AdminNavBar } from "@/components/AdminNavBar";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <AdminNavBar />
      <main className="flex-1">{children}</main>
    </div>
  );
}
