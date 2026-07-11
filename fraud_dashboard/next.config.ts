import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // `all-the-cities` lit son fichier binaire `cities.pbf` relatif à son propre
  // dossier au runtime : il doit rester hors du bundle webpack pour que ce
  // chemin reste valide (sinon ENOENT dans .next/server/vendor-chunks/).
  serverExternalPackages: ["all-the-cities"]
};

export default nextConfig;
