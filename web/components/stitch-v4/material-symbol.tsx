export function StitchV4MaterialSymbol({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  return (
    <span aria-hidden="true" className={`material-symbols-outlined ${className}`.trim()}>
      {name}
    </span>
  );
}
