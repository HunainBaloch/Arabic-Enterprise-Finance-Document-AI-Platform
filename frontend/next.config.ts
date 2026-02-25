const nextConfig: any = {
  output: "standalone",
  env: {
    // Inside Docker the backend is reachable via service name
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;
