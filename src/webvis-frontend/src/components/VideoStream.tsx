import { useEffect, useState } from "react";

// src/components/VideoStream.tsx
type Props = { url: string };

export function VideoStream({ url }: Props) {
  // MJPEG streams work perfectly as <img src="...">
  return (
    <div style={{ display: "grid" }}>
      {/* eslint-disable-next-line jsx-a11y/alt-text */}
      <img
        src={url}
        style={{
          width: "100%",
          maxHeight: 480,
          objectFit: "cover",
          borderRadius: 8,
          border: "1px solid #334155",
          background: "#0b1220",
        }}
      />
    </div>
  );
}
