export function Logo({ size = 32 }: { size?: number }) {
  const id = `grad-${size}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="32" height="32" rx="8" fill={`url(#${id})`} />
      {/* North-star mark — four-pointed star representing guidance & expertise */}
      <path
        d="M16 7L18.5 13.5L25 16L18.5 18.5L16 25L13.5 18.5L7 16L13.5 13.5Z"
        fill="white"
        fillOpacity="0.95"
      />
      <circle cx="16" cy="16" r="1.75" fill="url(#innerGrad)" />
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#6366f1" />
          <stop offset="1" stopColor="#7c3aed" />
        </linearGradient>
        <linearGradient id="innerGrad" x1="14" y1="14" x2="18" y2="18" gradientUnits="userSpaceOnUse">
          <stop stopColor="#a5b4fc" />
          <stop offset="1" stopColor="#c4b5fd" />
        </linearGradient>
      </defs>
    </svg>
  );
}
