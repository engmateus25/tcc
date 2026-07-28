export function requiredEnv(key: string): string {
  const value = import.meta.env[key];
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }

  throw new Error(
    `Variavel de ambiente obrigatoria ausente: ${key}. ` +
      "Crie frontend/.env a partir de frontend/.env.example.",
  );
}

export function optionalEnv(key: string, fallback = ""): string {
  const value = import.meta.env[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

export function booleanEnv(key: string, fallback = false): boolean {
  const value = optionalEnv(key);
  if (!value) return fallback;
  return ["1", "true", "sim", "yes", "on"].includes(value.toLowerCase());
}

export const API_BASE_URL = optionalEnv("VITE_AI_BASE_URL", "http://127.0.0.1:8000");
