"use client";
import { useEffect, useRef } from "react";

/** A static topographic illustration. Workflow status is shown only in the live graph. */
export default function Contour() {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const el = canvas.current;
    const ctx = el?.getContext("2d");
    if (!el || !ctx) return;
    function draw() {
      if (!el || !ctx) return;
      const {width, height} = el.getBoundingClientRect();
      const scale = Math.min(window.devicePixelRatio || 1, 2);
      el.width = Math.round(width * scale);
      el.height = Math.round(height * scale);
      ctx.setTransform(scale * width / 520,0,0,scale * height / 240,0,0);
      for (let ring = 1; ring <= 55; ring++) {
        ctx.beginPath();
        for (let i = 0; i <= 300; i++) {
          const angle = i / 300 * Math.PI * 2;
          const radius = ring * (3.8 + .72 * Math.cos(3*angle + ring/38) + .32 * Math.sin(5*angle));
          const x = 297 + 1.38 * radius * Math.cos(angle) + 9 * Math.sin(ring/10);
          const y = 120 + .74 * radius * Math.sin(angle) - .24 * radius * Math.cos(angle);
          if (i === 0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
        }
        ctx.strokeStyle = ring % 5 === 0 ? "#c4d1a8" : "#748a79";
        ctx.lineWidth = ring % 5 === 0 ? 1.1 : .65;
        ctx.stroke();
      }
    }
    const observer = new ResizeObserver(draw);
    observer.observe(el);
    draw();
    return () => observer.disconnect();
  }, []);
  return <canvas ref={canvas} aria-hidden="true" className="contour" />;
}
