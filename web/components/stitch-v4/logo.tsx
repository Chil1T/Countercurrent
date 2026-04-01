export function StitchV4Logo({
  className = "",
}: {
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 640 640"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={className}
    >
      <path
        d="M85 180 H470 C545 180, 575 245, 575 320 C575 395, 545 460, 470 460 H85 C165 460, 210 400, 210 320 C210 240, 165 180, 85 180 Z"
        fill="#1E6BFF"
      />
      <g
        fill="none"
        stroke="#FFFFFF"
        strokeWidth="20"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M210 220 C275 235, 330 275, 365 370" />
        <path d="M520 220 C455 235, 400 275, 365 370" />
      </g>
    </svg>
  );
}
