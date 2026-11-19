const origin = process.env.AURA_API_ORIGIN || "http://127.0.0.1:8000";
export default {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/aura/:path*",
        destination: new URL("/:path*", origin).href,
      },
    ];
  },
};
