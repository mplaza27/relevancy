import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";

export function ScrollToBottom() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const check = () => {
      const scrollBottom = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
      setVisible(scrollBottom > 400);
    };

    check();
    window.addEventListener("scroll", check, { passive: true });
    window.addEventListener("resize", check, { passive: true });
    return () => {
      window.removeEventListener("scroll", check);
      window.removeEventListener("resize", check);
    };
  }, []);

  if (!visible) return null;

  return (
    <button
      className="
        fixed bottom-6 right-6 z-40
        w-10 h-10 rounded-full
        bg-[#15314b] text-white shadow-lg
        flex items-center justify-center
        hover:bg-[#3172ae] transition-colors
      "
      onClick={() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" })}
      title="Jump to bottom"
    >
      <ChevronDown className="w-5 h-5" />
    </button>
  );
}
