// 랭킹에 쓰는 빵 캐릭터 (쇼케이스 랭킹 화면). 사용자마다 user_id로 몸통이
// 정해지고, 1위는 왕관 쓴 번, 내 아바타는 깃발 꽂은 번으로 고정한다.

const CRUST = "#f5b041";
const EDGE = "#e67e22";
const EYE = "#3b2a1a";

type Body = "croissant" | "bun" | "saltBread" | "soboro" | "toast";
export type BreadVariant = Body | "king" | "flag";

const ROTATION: Body[] = ["croissant", "saltBread", "soboro", "toast", "bun"];

/** 눈·입·볼. 얼굴 위치만 몸통마다 다르다. */
function Face({ y }: { y: number }) {
  return (
    <>
      <circle cx="25" cy={y} r="2.3" fill={EYE} />
      <circle cx="39" cy={y} r="2.3" fill={EYE} />
      <path
        d={`M28 ${y + 5} Q32 ${y + 9} 36 ${y + 5}`}
        fill="none"
        stroke={EYE}
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="20" cy={y + 4} r="3" fill="#ff6a4d" opacity=".4" />
      <circle cx="44" cy={y + 4} r="3" fill="#ff6a4d" opacity=".4" />
    </>
  );
}

function Shape({ variant }: { variant: BreadVariant }) {
  switch (variant) {
    case "croissant":
      return (
        <>
          <ellipse cx="14" cy="38" rx="9" ry="14" transform="rotate(-38 14 38)" fill={CRUST} stroke={EDGE} strokeWidth="2" />
          <ellipse cx="50" cy="38" rx="9" ry="14" transform="rotate(38 50 38)" fill={CRUST} stroke={EDGE} strokeWidth="2" />
          <ellipse cx="32" cy="34" rx="15" ry="19" fill={CRUST} stroke={EDGE} strokeWidth="2" />
          <path d="M20 22q12 -6 24 0" fill="none" stroke={EDGE} strokeWidth="2" strokeLinecap="round" />
          <Face y={36} />
        </>
      );
    case "saltBread":
      return (
        <>
          <ellipse cx="32" cy="38" rx="25" ry="17" fill={CRUST} stroke={EDGE} strokeWidth="2" />
          {[[22, 27, 1.7], [32, 24, 1.7], [42, 27, 1.7], [27, 23, 1.4], [38, 23, 1.4]].map(([cx, cy, r]) => (
            <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r={r} fill="#fff" />
          ))}
          <Face y={40} />
        </>
      );
    case "soboro":
      return (
        <>
          <circle cx="32" cy="36" r="23" fill={CRUST} stroke={EDGE} strokeWidth="2" />
          {[[22, 22], [32, 18], [42, 22], [17, 32], [47, 32], [27, 26], [38, 26]].map(([cx, cy]) => (
            <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="2.2" fill={EDGE} />
          ))}
          <Face y={40} />
        </>
      );
    case "toast":
      return (
        <>
          <path
            d="M14 30C8 30 8 17 18 17C22 11 42 11 46 17C56 17 56 30 50 30L50 51Q50 55 46 55L18 55Q14 55 14 51Z"
            fill="#f7d58a"
            stroke={EDGE}
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <rect x="21" y="32" width="10" height="7" rx="1.5" fill="#ffe873" stroke="#e0b800" strokeWidth="1.2" />
          <Face y={44} />
        </>
      );
    case "bun":
    case "king":
      return (
        <>
          <ellipse cx="32" cy="40" rx="24" ry="19" fill={CRUST} stroke={EDGE} strokeWidth="2" />
          <path d="M22 26l4 6M32 23v7M42 26l-4 6" stroke={EDGE} strokeWidth="2.6" strokeLinecap="round" fill="none" />
          <Face y={42} />
          {variant === "king" && (
            <>
              <path d="M21 17L24 5l8 7 8-7 3 12z" fill="#ffb800" stroke="#d99a00" strokeWidth="1.6" strokeLinejoin="round" />
              <circle cx="24" cy="5" r="1.8" fill="#ffb800" />
              <circle cx="40" cy="5" r="1.8" fill="#ffb800" />
            </>
          )}
        </>
      );
    case "flag":
      return (
        <>
          <ellipse cx="32" cy="42" rx="22" ry="17" fill={CRUST} stroke={EDGE} strokeWidth="2" />
          <path d="M32 26V6" stroke="#6b4a2b" strokeWidth="2.4" strokeLinecap="round" />
          <path d="M32 6l15 5-15 6z" fill="#ff5a1f" />
          <Face y={44} />
        </>
      );
  }
}

export function breadFor(userId: number): Body {
  return ROTATION[Math.abs(userId) % ROTATION.length];
}

export function BreadAvatar({
  variant,
  size = 40,
}: {
  variant: BreadVariant;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-hidden="true"
      style={{ flexShrink: 0, display: "block" }}
    >
      <Shape variant={variant} />
    </svg>
  );
}
