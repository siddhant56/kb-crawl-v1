import { redirect } from "next/navigation";

// Root path → redirect to /chat.
// The middleware will send unauthenticated users to /login.
export default function Home() {
  redirect("/chat");
}
